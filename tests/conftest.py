import os
import stat
import zipfile
from pathlib import Path

import pytest

ACSM = (
    '<?xml version="1.0"?>'
    '<fulfillmentToken xmlns="http://ns.adobe.com/adept">'
    "<operatorURL>https://store.invalid/fulfillment</operatorURL>"
    "</fulfillmentToken>"
)


def _entry(name: str) -> zipfile.ZipInfo:
    # A fixed time: Python 3.14 takes it from SOURCE_DATE_EPOCH when set, and
    # Nix shells set that to the zip format's own epoch, which 3.14.4 converts
    # in local time and so fails to pack west of UTC.
    return zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))


CONTAINER = (
    "<container xmlns='urn:oasis:names:tc:opendocument:xmlns:container'>"
    "<rootfiles><rootfile full-path='OEBPS/package.opf'/></rootfiles></container>"
)


def make_epub(
    path: Path,
    *,
    rights: bool = False,
    algorithms: tuple = (),
    title: str | None = "A Synthetic Book",
    metadata: str | None = None,
    manifest: str = "",
    files: dict[str, bytes] | None = None,
    version: str = "3.0",
) -> Path:
    """An EPUB whose OPF metadata is title alone, or the given XML."""
    if metadata is None:
        metadata = f"<dc:title>{title}</dc:title>" if title else ""
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(_entry("mimetype"), "application/epub+zip")
        z.writestr(_entry("META-INF/container.xml"), CONTAINER)
        z.writestr(
            _entry("OEBPS/package.opf"),
            f"<package xmlns='http://www.idpf.org/2007/opf' version='{version}' "
            "xmlns:opf='http://www.idpf.org/2007/opf'>"
            "<metadata xmlns:dc='http://purl.org/dc/elements/1.1/'>"
            f"{metadata}</metadata><manifest>{manifest}</manifest></package>",
        )
        z.writestr(_entry("OEBPS/chapter.xhtml"), "<html><body>text</body></html>")
        for name, content in (files or {}).items():
            z.writestr(_entry(name), content)
        if rights:
            z.writestr(_entry("META-INF/rights.xml"), "<rights/>")
        if algorithms:
            methods = "".join(
                "<EncryptedData xmlns='http://www.w3.org/2001/04/xmlenc#'>"
                f"<EncryptionMethod Algorithm='{a}'/></EncryptedData>"
                for a in algorithms
            )
            z.writestr(
                _entry("META-INF/encryption.xml"),
                "<encryption xmlns='urn:oasis:names:tc:opendocument:xmlns:container'>"
                f"{methods}</encryption>",
            )
    return path


def drm_epub(path: Path) -> Path:
    return make_epub(
        path, rights=True, algorithms=("http://www.w3.org/2001/04/xmlenc#aes128-cbc",)
    )


# Each stand-in takes `-D <key dir> -o <output> <input>`, as bookdrop calls the
# real tools, refuses a key directory missing any file, and copies in the file
# named by its environment variable.
STUB = """#!/bin/sh
for f in device.xml activation.xml devicesalt; do
  [ -f "$2/$f" ] || { echo "Error : $2/$f doesn't exists"; exit 255; }
done
# libgourou writes here on meeting a new licence service.
echo touched >> "$2/activation.xml" || exit 255
[ -n "${VAR}" ] || { echo "Error : stand-in told to fail"; exit 255; }
cp "${VAR}" "$4"
"""


@pytest.fixture
def tools(tmp_path, monkeypatch):
    """Stand-ins for acsmdownloader and adept_remove, first on PATH."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool, var in (
        ("acsmdownloader", "STUB_FULFILLED"),
        ("adept_remove", "STUB_STRIPPED"),
    ):
        script = bin_dir / tool
        script.write_text(STUB.replace("VAR", var))
        script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return bin_dir


@pytest.fixture
def adept_dir(tmp_path):
    """A device key laid out as the deployment mounts it: read-only."""
    key = tmp_path / "adept"
    key.mkdir()
    for name in ("device.xml", "activation.xml", "devicesalt"):
        (key / name).write_text(name)
        (key / name).chmod(stat.S_IRUSR)
    key.chmod(stat.S_IRUSR | stat.S_IXUSR)
    yield key
    key.chmod(stat.S_IRWXU)
