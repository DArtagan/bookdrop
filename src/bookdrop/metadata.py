import posixpath
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

DC = "{http://purl.org/dc/elements/1.1/}"
OPF = "{http://www.idpf.org/2007/opf}"

# ONIX code list 5, which EPUB 3 uses to type an identifier: 15 is ISBN-13,
# 02 is ISBN-10.
ONIX_ISBN = {"15", "02"}

# The cover is served from bookdrop's own origin with the type the book claims,
# so an SVG, which can carry script, is never one.
COVER_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


@dataclass
class Metadata:
    title: str = ""
    authors: list[str] = field(default_factory=list)
    series: str = ""
    series_index: str = ""
    isbn: str = ""
    publisher: str = ""
    date: str = ""
    description: str = ""
    language: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Metadata:
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in names})


def read(book: Path) -> Metadata:
    """What the book says about itself. Empty for anything but a readable EPUB."""
    opf = _opf(book)
    if opf is None:
        return Metadata()
    package, _ = opf
    meta = package.find(f"{OPF}metadata")
    if meta is None:
        meta = package.find("metadata")
    if meta is None:
        return Metadata()
    refines = _refinements(meta)
    series, index = _series(meta, refines)
    return Metadata(
        title=_title(meta, refines),
        authors=_authors(meta, refines),
        series=series,
        series_index=index,
        isbn=_isbn(meta, refines),
        publisher=_text(meta.find(f"{DC}publisher")),
        date=_text(meta.find(f"{DC}date")) or _property(meta, "dcterms:date"),
        description=_text(meta.find(f"{DC}description")),
        language=_text(meta.find(f"{DC}language")),
    )


def cover(book: Path) -> tuple[bytes, str] | None:
    """The cover image's bytes and media type, as the OPF names it."""
    opf = _opf(book)
    if opf is None:
        return None
    package, opf_path = opf
    manifest = package.find(f"{OPF}manifest")
    if manifest is None:
        return None
    items = manifest.findall(f"{OPF}item")
    # EPUB 3 marks the item; EPUB 2 names its id in a meta.
    item = next(
        (i for i in items if "cover-image" in (i.get("properties") or "").split()),
        None,
    )
    if item is None:
        cover_id = next(
            (m.get("content") for m in package.iter() if m.get("name") == "cover"),
            None,
        )
        item = next((i for i in items if i.get("id") == cover_id), None)
    if item is None or item.get("media-type") not in COVER_TYPES:
        return None
    href = posixpath.normpath(
        posixpath.join(posixpath.dirname(opf_path), item.get("href", ""))
    )
    try:
        with zipfile.ZipFile(book) as z:
            return z.read(href), item.get("media-type")
    except KeyError:
        return None


def _opf(book: Path) -> tuple[ET.Element, str] | None:
    try:
        with zipfile.ZipFile(book) as z:
            container = ET.fromstring(z.read("META-INF/container.xml"))
            rootfile = next(
                e for e in container.iter() if e.tag.rsplit("}", 1)[-1] == "rootfile"
            )
            path = rootfile.get("full-path", "")
            return ET.fromstring(z.read(path)), path
    except zipfile.BadZipFile, KeyError, StopIteration, ET.ParseError:
        return None


def _text(element: ET.Element | None) -> str:
    return " ".join((element.text or "").split()) if element is not None else ""


def _property(meta: ET.Element, name: str) -> str:
    for m in meta.iter(f"{OPF}meta"):
        if m.get("property") == name and not m.get("refines"):
            return _text(m)
    return ""


def _refinements(meta: ET.Element) -> dict[str, dict[str, str]]:
    """EPUB 3's <meta refines="#id" property="p">v</meta>, as {id: {p: v}}."""
    out: dict[str, dict[str, str]] = {}
    for m in meta.iter(f"{OPF}meta"):
        target = (m.get("refines") or "").lstrip("#")
        if target and m.get("property"):
            out.setdefault(target, {})[m.get("property")] = _text(m)
    return out


def _title(meta: ET.Element, refines: dict) -> str:
    titles = meta.findall(f"{DC}title")
    main = [
        t for t in titles if refines.get(t.get("id"), {}).get("title-type") == "main"
    ]
    return _text((main or titles or [None])[0])


def _authors(meta: ET.Element, refines: dict) -> list[str]:
    def role(creator: ET.Element) -> str:
        return creator.get(f"{OPF}role") or refines.get(creator.get("id"), {}).get(
            "role", ""
        )

    creators = meta.findall(f"{DC}creator")
    authors = [c for c in creators if role(c) in ("", "aut")] or creators
    return [name for c in authors if (name := _text(c))]


def _series(meta: ET.Element, refines: dict) -> tuple[str, str]:
    calibre = {
        m.get("name"): m.get("content", "")
        for m in meta.iter(f"{OPF}meta")
        if (m.get("name") or "").startswith("calibre:series")
    }
    if calibre.get("calibre:series"):
        return calibre["calibre:series"], _index(
            calibre.get("calibre:series_index", "")
        )
    for m in meta.iter(f"{OPF}meta"):
        if m.get("property") != "belongs-to-collection":
            continue
        refined = refines.get(m.get("id"), {})
        if refined.get("collection-type", "series") == "series":
            return _text(m), _index(refined.get("group-position", ""))
    return "", ""


def _index(value: str) -> str:
    """'2.0' as '2', '3.5' as itself; anything unreadable as given."""
    try:
        number = float(value)
    except ValueError:
        return value.strip()
    return str(int(number)) if number.is_integer() else str(number)


def _isbn(meta: ET.Element, refines: dict) -> str:
    for identifier in meta.findall(f"{DC}identifier"):
        scheme = (identifier.get(f"{OPF}scheme") or "").lower()
        typed = refines.get(identifier.get("id"), {}).get("identifier-type")
        text = _text(identifier)
        claims_isbn = (
            scheme == "isbn"
            or typed in ONIX_ISBN
            or text.lower().startswith(("urn:isbn:", "isbn:"))
        )
        if claims_isbn and (isbn := normalise_isbn(text)):
            return isbn
    # A Kobo EPUB names only the print edition it was made from.
    for source in meta.findall(f"{DC}source"):
        if isbn := normalise_isbn(_text(source)):
            return isbn
    return ""


def normalise_isbn(text: str) -> str:
    """The ISBN in text, digits only, if its check digit holds; else ""."""
    digits = re.sub(r"[^0-9Xx]", "", re.sub(r"(?i)^(urn:)?isbn:", "", text)).upper()
    if len(digits) == 13 and digits.isdigit():
        total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(digits))
        return digits if total % 10 == 0 else ""
    if len(digits) == 10 and digits[:9].isdigit():
        total = sum(
            (10 if d == "X" else int(d)) * (10 - i) for i, d in enumerate(digits)
        )
        return digits if total % 11 == 0 else ""
    return ""
