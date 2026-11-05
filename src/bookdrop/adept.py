import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

KEY_FILES = ("device.xml", "activation.xml", "devicesalt")

# Font obfuscation, which every reader undoes itself. Anything else listed in an
# EPUB's encryption.xml is DRM.
FONT_OBFUSCATION = {
    "http://www.idpf.org/2008/embedding",
    "http://ns.adobe.com/pdf/enc#RC",
}

TOOL_TIMEOUT = 300


class Refused(Exception):
    """An upload bookdrop will not take, with the reason a person reads."""


@dataclass(frozen=True)
class Prepared:
    book: Path
    # How the upload became a DRM-free book, said to the person who dropped it.
    preparation: str


def kind(path: Path) -> str:
    """What a file is by its content, never its name: "acsm", "epub" or "pdf"."""
    with path.open("rb") as f:
        head = f.read(5)
    if head == b"%PDF-":
        return "pdf"
    if head.startswith(b"PK"):
        try:
            with zipfile.ZipFile(path) as z:
                if z.read("mimetype").strip() == b"application/epub+zip":
                    return "epub"
        except zipfile.BadZipFile, KeyError:
            pass
        raise Refused("This is a zip file but not an EPUB.")
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        raise Refused("Only an .acsm, an EPUB or a PDF can be dropped.") from None
    if root.tag.rsplit("}", 1)[-1] == "fulfillmentToken":
        return "acsm"
    raise Refused("This XML file is not an .acsm.")


def encrypted(path: Path, file_kind: str) -> bool:
    if file_kind == "pdf":
        return b"/Encrypt" in path.read_bytes()
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        if "META-INF/rights.xml" in names:
            return True
        if "META-INF/encryption.xml" not in names:
            return False
        root = ET.fromstring(z.read("META-INF/encryption.xml"))
    algorithms = {
        e.get("Algorithm")
        for e in root.iter()
        if e.tag.rsplit("}", 1)[-1] == "EncryptionMethod"
    }
    return bool(algorithms - FONT_OBFUSCATION)


def prepare(upload: Path, out_dir: Path, adept_dir: Path) -> Prepared:
    """Turn an upload into a DRM-free book in out_dir, or raise Refused."""
    upload_kind = kind(upload)
    fulfilled_from_store = upload_kind == "acsm"
    if fulfilled_from_store:
        fulfilled = out_dir / "fulfilled"
        _run(adept_dir, "acsmdownloader", "-o", str(fulfilled), str(upload))
        if not fulfilled.exists():
            raise Refused("The store sent nothing for this .acsm.")
        book_kind = kind(fulfilled)
        source = fulfilled.rename(fulfilled.with_suffix(f".{book_kind}"))
    else:
        book_kind = upload_kind
        source = upload
    book = out_dir / f"book.{book_kind}"
    if encrypted(source, book_kind):
        _run(adept_dir, "adept_remove", "-o", str(book), str(source))
        if encrypted(book, book_kind):
            raise Refused("The DRM could not be removed from this book.")
        preparation = (
            "Downloaded from the store, DRM removed."
            if fulfilled_from_store
            else "DRM removed."
        )
    else:
        shutil.copyfile(source, book)
        preparation = (
            "Downloaded from the store, which sent it DRM-free."
            if fulfilled_from_store
            else "It arrived DRM-free."
        )
    return Prepared(book, preparation)


def _run(adept_dir: Path, tool: str, *args: str) -> None:
    # libgourou rewrites activation.xml the first time it meets a store's licence
    # service, and the deployment mounts the key read-only. A scratch copy per run
    # lets that write succeed; it is fetched again next time, which is harmless.
    with tempfile.TemporaryDirectory() as key:
        for name in KEY_FILES:
            shutil.copyfile(adept_dir / name, Path(key) / name)
        try:
            result = subprocess.run(
                [tool, "-D", key, *args],
                capture_output=True,
                text=True,
                timeout=TOOL_TIMEOUT,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise Refused(
                f"{tool} did not finish within {TOOL_TIMEOUT} seconds."
            ) from None
    if result.returncode != 0:
        detail = (result.stdout + result.stderr).strip().splitlines()
        raise Refused(f"{tool} failed: {detail[-1] if detail else 'no output'}")
