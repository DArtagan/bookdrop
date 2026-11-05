import io
import posixpath
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from lxml import etree

from bookdrop.metadata import Metadata, normalise_isbn

OPF = "http://www.idpf.org/2007/opf"
DC = "http://purl.org/dc/elements/1.1/"

# Stump matches these by their literal text, not their namespaces: a tag named
# "dc:title", an attribute named "opf:scheme". Every element bookdrop writes
# therefore spells them so, declaring the namespaces itself; see _element.
NSMAP = {"dc": DC, "opf": OPF}
# Where bookdrop's elements go, kept as a comment until they are spliced in.
MARKER = "bookdrop"

# The metadata bookdrop owns, each removed before it is written afresh. What the
# book carries besides, rights, accessibility, its own identifier, stays.
OWNED_DC = ("title", "publisher", "date", "description", "subject")
OWNED_META_NAMES = ("calibre:series", "calibre:series_index", "calibre:title_sort")
ARTICLES = ("The", "A", "An")


def rewrite(book: Path, meta: Metadata) -> bytes:
    """The EPUB at book with meta written into its OPF, every other entry as is."""
    out = io.BytesIO()
    with zipfile.ZipFile(book) as source, zipfile.ZipFile(out, "w") as target:
        opf_path = _rootfile(source)
        for info in source.infolist():
            data = source.read(info)
            if info.filename == opf_path:
                data = rewrite_opf(data, meta)
            # A fresh entry rather than the source's, whose extra fields and
            # flags describe the old bytes. The order, and with it the stored
            # mimetype first, is the source's.
            entry = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            entry.compress_type = info.compress_type
            entry.external_attr = info.external_attr
            target.writestr(entry, data)
    return out.getvalue()


def rewrite_opf(data: bytes, meta: Metadata) -> bytes:
    root = etree.fromstring(data, etree.XMLParser(remove_blank_text=False))
    metadata = root.find(f"{{{OPF}}}metadata")
    if metadata is None:
        raise ValueError("the OPF has no metadata element")
    unique_id = root.get("unique-identifier")
    removed: set[str] = set()

    def remove(element: etree._Element) -> None:
        if element.get("id"):
            removed.add(element.get("id"))
        element.getparent().remove(element)

    for name in OWNED_DC:
        for element in metadata.findall(f"{{{DC}}}{name}"):
            remove(element)
    if meta.language:
        for element in metadata.findall(f"{{{DC}}}language"):
            remove(element)
    for creator in metadata.findall(f"{{{DC}}}creator"):
        if _role(creator, metadata) in ("", "aut"):
            remove(creator)
    for identifier in metadata.findall(f"{{{DC}}}identifier"):
        # The package's own identifier stays even when it is an ISBN.
        unique = unique_id is not None and identifier.get("id") == unique_id
        if not unique and normalise_isbn(identifier.text or ""):
            remove(identifier)
    for element in list(metadata.iter(f"{{{OPF}}}meta")):
        if (
            element.get("name") in OWNED_META_NAMES
            or element.get("property") == "belongs-to-collection"
            and _refined(metadata, element.get("id"), "collection-type")
            in ("", "series")
            or element.get("property") == "dcterms:date"
            and meta.date
        ):
            remove(element)
    for element in list(metadata.iter(f"{{{OPF}}}meta")):
        if (element.get("refines") or "").lstrip("#") in removed:
            remove(element)
    for element in metadata.iter(f"{{{OPF}}}meta"):
        # EPUB 3 requires the time of the last change.
        if element.get("property") == "dcterms:modified":
            element.text = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    metadata.append(etree.Comment(MARKER))
    text = etree.tostring(root, xml_declaration=True, encoding="utf-8")
    written = b"".join(_elements(meta, epub3=root.get("version", "").startswith("3")))
    return text.replace(f"<!--{MARKER}-->".encode(), written, 1)


def sidecar(meta: Metadata, cover: bool) -> bytes:
    """metadata.opf as Calibre writes it beside a book: OPF 2.0 and its own id."""
    book_id = _element(
        "dc:identifier", str(uuid.uuid4()), {"opf:scheme": "uuid", "id": "uuid_id"}
    )
    guide = (
        b'<guide><reference type="cover" title="Cover" href="cover.jpg"/></guide>'
        if cover
        else b""
    )
    return (
        b"<?xml version='1.0' encoding='utf-8'?>\n"
        b'<package xmlns="http://www.idpf.org/2007/opf" '
        b'unique-identifier="uuid_id" version="2.0"><metadata>'
        + book_id
        + b"".join(_elements(meta, epub3=False))
        + b"</metadata>"
        + guide
        + b"</package>\n"
    )


def title_sort(title: str, language: str) -> str:
    """'The Way of Kings' as 'Way of Kings, The', as Calibre sorts English."""
    if language and not language.lower().startswith("en"):
        return title
    for article in ARTICLES:
        if title.startswith(f"{article} ") and len(title) > len(article) + 1:
            return f"{title[len(article) + 1 :]}, {article}"
    return title


def _elements(meta: Metadata, epub3: bool) -> list[bytes]:
    """bookdrop's metadata as OPF elements, in the forms the package's version
    allows, but for the ISBN. EPUB 3 dropped the opf: attributes in favour of
    refinements, and Stump reads an ISBN only as opf:scheme, so an EPUB 3 book
    gets both on one element: Stump reads one, other readers the other, and
    epubcheck reports the attribute as its one error (Will, 2026-11-05)."""
    out = [_element("dc:title", meta.title)]
    for number, name in enumerate(meta.authors, 1):
        if epub3:
            out.append(
                _element("dc:creator", name, {"id": f"bookdrop-creator-{number}"})
            )
            out.append(
                _refinement(
                    f"bookdrop-creator-{number}", "role", "aut", "marc:relators"
                )
            )
        else:
            out.append(_element("dc:creator", name, {"opf:role": "aut"}))
    if meta.isbn and epub3:
        out.append(
            _element(
                "dc:identifier",
                meta.isbn,
                {"id": "bookdrop-isbn", "opf:scheme": "ISBN"},
            )
        )
        # ONIX code list 5: 15 is ISBN-13, 02 ISBN-10.
        onix = "15" if len(meta.isbn) == 13 else "02"
        out.append(
            _refinement("bookdrop-isbn", "identifier-type", onix, "onix:codelist5")
        )
    elif meta.isbn:
        out.append(_element("dc:identifier", meta.isbn, {"opf:scheme": "ISBN"}))
    for name in ("publisher", "date", "description", "language"):
        if value := getattr(meta, name):
            out.append(_element(f"dc:{name}", value))
    out += [_element("dc:subject", genre) for genre in meta.genres]
    if meta.series:
        out.append(_meta("calibre:series", meta.series))
        if meta.series_index:
            out.append(_meta("calibre:series_index", meta.series_index))
    out.append(_meta("calibre:title_sort", title_sort(meta.title, meta.language)))
    return out


def _element(name: str, text: str, attributes: dict[str, str] | None = None) -> bytes:
    """One standalone element, its namespaces declared on itself.

    Built apart from the document: lxml drops a declaration whose namespace is
    already in scope under another prefix when an element is moved in, and the
    OPF namespace is in scope as the default, so opf:scheme would come out as
    ns0:scheme, which Stump does not read.
    """
    prefix, local = name.split(":")
    element = etree.Element(f"{{{NSMAP[prefix]}}}{local}", nsmap=NSMAP)
    for key, value in (attributes or {}).items():
        if ":" in key:
            key_prefix, key_local = key.split(":")
            key = f"{{{NSMAP[key_prefix]}}}{key_local}"
        element.set(key, value)
    element.text = text
    return etree.tostring(element, encoding="utf-8")


def _meta(name: str, content: str) -> bytes:
    element = etree.Element(f"{{{OPF}}}meta", nsmap={None: OPF})
    element.set("name", name)
    element.set("content", content)
    return etree.tostring(element, encoding="utf-8")


def _refinement(target: str, prop: str, text: str, scheme: str) -> bytes:
    element = etree.Element(f"{{{OPF}}}meta", nsmap={None: OPF})
    element.set("refines", f"#{target}")
    element.set("property", prop)
    element.set("scheme", scheme)
    element.text = text
    return etree.tostring(element, encoding="utf-8")


def _role(creator: etree._Element, metadata: etree._Element) -> str:
    return creator.get(f"{{{OPF}}}role") or _refined(
        metadata, creator.get("id"), "role"
    )


def _refined(metadata: etree._Element, element_id: str | None, prop: str) -> str:
    if not element_id:
        return ""
    for element in metadata.iter(f"{{{OPF}}}meta"):
        if (
            element.get("refines") == f"#{element_id}"
            and element.get("property") == prop
        ):
            return (element.text or "").strip()
    return ""


def _rootfile(book: zipfile.ZipFile) -> str:
    container = etree.fromstring(book.read("META-INF/container.xml"))
    rootfile = next(
        (e for e in container.iter() if etree.QName(e).localname == "rootfile"),
        None,
    )
    if rootfile is None:
        raise ValueError("the container names no OPF")
    return posixpath.normpath(rootfile.get("full-path", ""))
