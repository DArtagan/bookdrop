import zipfile

import pytest
from conftest import make_epub

from bookdrop.metadata import cover, normalise_isbn, read

# Shaped as Calibre writes the library's own sidecars: OPF 2.0, opf:role,
# opf:scheme, calibre:series.
CALIBRE = """
<dc:title>Dune Messiah</dc:title>
<dc:creator opf:role="aut" opf:file-as="Herbert, Frank">Frank Herbert</dc:creator>
<dc:creator opf:role="ill">Someone Else</dc:creator>
<dc:identifier opf:scheme="calibre">15</dc:identifier>
<dc:identifier opf:scheme="ISBN">9780441015610</dc:identifier>
<dc:publisher>Ace</dc:publisher>
<dc:date>1969-01-01T00:00:00+00:00</dc:date>
<dc:language>eng</dc:language>
<meta name="calibre:series" content="Dune"/>
<meta name="calibre:series_index" content="2.0"/>
"""

# Shaped as the first Kobo purchase was on 2026-11-03: the ISBN only in
# dc:source, dc:identifier a UUID, the date as a dcterms:date meta.
KOBO = """
<dc:title id="title">The Book</dc:title>
<meta refines="#title" property="title-type">main</meta>
<dc:source id="src-id">urn:isbn:9780374248529</dc:source>
<meta refines="#src-id" property="identifier-type" scheme="onix:codelist5">15</meta>
<dc:identifier id="uid">urn:uuid:0b4f5a1e-2c3d-4e5f-8a9b-0c1d2e3f4a5b</dc:identifier>
<dc:language>en-US</dc:language>
<dc:creator>An Author</dc:creator>
<dc:publisher>A Publisher</dc:publisher>
<meta property="dcterms:date">2021</meta>
"""

EPUB3_SERIES = """
<dc:title id="t1">Subtitle Edition</dc:title>
<meta refines="#t1" property="title-type">subtitle</meta>
<dc:title id="t2">The Way of Kings</dc:title>
<meta refines="#t2" property="title-type">main</meta>
<dc:creator id="c1">Brandon Sanderson</dc:creator>
<meta refines="#c1" property="role" scheme="marc:relators">aut</meta>
<dc:creator id="c2">A Translator</dc:creator>
<meta refines="#c2" property="role" scheme="marc:relators">trl</meta>
<dc:identifier id="i1">9780765376671</dc:identifier>
<meta refines="#i1" property="identifier-type" scheme="onix:codelist5">15</meta>
<meta property="belongs-to-collection" id="s1">The Stormlight Archive</meta>
<meta refines="#s1" property="collection-type">series</meta>
<meta refines="#s1" property="group-position">1</meta>
"""


def test_calibre_opf(tmp_path):
    meta = read(make_epub(tmp_path / "b.epub", metadata=CALIBRE, version="2.0"))
    assert meta.title == "Dune Messiah"
    assert meta.authors == ["Frank Herbert"]
    assert (meta.series, meta.series_index) == ("Dune", "2")
    assert meta.isbn == "9780441015610"
    assert meta.publisher == "Ace"
    assert meta.language == "eng"


def test_kobo_opf(tmp_path):
    meta = read(make_epub(tmp_path / "b.epub", metadata=KOBO))
    assert meta.title == "The Book"
    assert meta.authors == ["An Author"]
    assert meta.isbn == "9780374248529"
    assert meta.date == "2021"
    assert (meta.series, meta.series_index) == ("", "")


def test_epub3_refinements(tmp_path):
    meta = read(make_epub(tmp_path / "b.epub", metadata=EPUB3_SERIES))
    assert meta.title == "The Way of Kings"
    assert meta.authors == ["Brandon Sanderson"]
    assert meta.isbn == "9780765376671"
    assert (meta.series, meta.series_index) == ("The Stormlight Archive", "1")


def test_a_collection_that_is_not_a_series_is_not_one(tmp_path):
    collection = """
    <dc:title>T</dc:title>
    <meta property="belongs-to-collection" id="s1">Award Winners</meta>
    <meta refines="#s1" property="collection-type">set</meta>
    """
    meta = read(make_epub(tmp_path / "b.epub", metadata=collection))
    assert meta.series == ""


def test_not_an_epub_reads_empty(tmp_path):
    bare = tmp_path / "bare.epub"
    with zipfile.ZipFile(bare, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype", (2020, 1, 1, 0, 0, 0)), "x")
    assert read(bare).title == ""
    pdf = tmp_path / "b.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    assert read(pdf).title == ""
    assert cover(pdf) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("9780374248529", "9780374248529"),
        ("urn:isbn:978-0-374-24852-9", "9780374248529"),
        ("9780374248528", ""),
        ("080442957X", "080442957X"),
        ("0804429571", ""),
        ("urn:uuid:0b4f5a1e-2c3d-4e5f-8a9b-0c1d2e3f4a5b", ""),
    ],
)
def test_normalise_isbn(text, expected):
    assert normalise_isbn(text) == expected


def test_a_uuid_is_never_taken_for_an_isbn(tmp_path):
    uuid_only = (
        "<dc:title>T</dc:title><dc:identifier>urn:uuid:9780374248529</dc:identifier>"
    )
    assert read(make_epub(tmp_path / "b.epub", metadata=uuid_only)).isbn == ""


JPEG = b"\xff\xd8\xff\xe0 not really a jpeg"


def test_epub3_cover(tmp_path):
    book = make_epub(
        tmp_path / "b.epub",
        manifest="<item id='c' href='images/c.jpg' media-type='image/jpeg' "
        "properties='cover-image'/>",
        files={"OEBPS/images/c.jpg": JPEG},
    )
    assert cover(book) == (JPEG, "image/jpeg")


def test_epub2_cover(tmp_path):
    book = make_epub(
        tmp_path / "b.epub",
        metadata="<dc:title>T</dc:title><meta name='cover' content='cimg'/>",
        manifest="<item id='cimg' href='c.jpg' media-type='image/jpeg'/>",
        files={"OEBPS/c.jpg": JPEG},
        version="2.0",
    )
    assert cover(book) == (JPEG, "image/jpeg")


def test_an_svg_cover_is_never_served(tmp_path):
    book = make_epub(
        tmp_path / "b.epub",
        manifest="<item id='c' href='c.svg' media-type='image/svg+xml' "
        "properties='cover-image'/>",
        files={"OEBPS/c.svg": b"<svg onload='alert(1)'/>"},
    )
    assert cover(book) is None
