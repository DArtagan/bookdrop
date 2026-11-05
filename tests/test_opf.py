import re
import zipfile

import pytest
from conftest import make_epub
from lxml import etree

from bookdrop.metadata import Metadata, read
from bookdrop.opf import rewrite, sidecar, title_sort

META = Metadata(
    title="The Way of Kings",
    authors=["Brandon Sanderson"],
    series="The Stormlight Archive",
    series_index="1",
    isbn="9780765376671",
    publisher="Tor",
    date="2010-08-31",
    description="Roshar & <storms>",
    language="en",
    genres=["Fantasy", "Fiction, fantasy, epic"],
)

# Shaped as the first Kobo purchase was: EPUB 3, refinements, the ISBN only in
# dc:source, the date as a dcterms:date meta, plus what bookdrop does not own.
EPUB3 = """
<dc:title id="t">Old Title</dc:title>
<meta refines="#t" property="title-type">main</meta>
<dc:creator id="c1">Old Author</dc:creator>
<meta refines="#c1" property="role" scheme="marc:relators">aut</meta>
<dc:creator id="c2">A Translator</dc:creator>
<meta refines="#c2" property="role" scheme="marc:relators">trl</meta>
<dc:identifier id="uid">urn:uuid:0b4f5a1e-2c3d-4e5f-8a9b-0c1d2e3f4a5b</dc:identifier>
<dc:source>urn:isbn:9780374248529</dc:source>
<dc:language>en-US</dc:language>
<dc:rights>All rights reserved</dc:rights>
<meta property="dcterms:date">2009</meta>
<meta property="dcterms:modified">2021-08-05T17:30:56Z</meta>
<meta property="schema:accessMode">textual</meta>
<meta property="belongs-to-collection" id="s">Old Series</meta>
<meta refines="#s" property="collection-type">series</meta>
"""

# Shaped as Calibre writes the library's books: OPF 2.0, opf: attributes.
EPUB2 = """
<dc:title>Old Title</dc:title>
<dc:creator opf:role="aut" opf:file-as="Author, Old">Old Author</dc:creator>
<dc:identifier opf:scheme="uuid" id="uuid_id">f87ebd82-0ec7-483a-85ba-c0c0cc3ba20f</dc:identifier>
<dc:identifier opf:scheme="ISBN">9780441015610</dc:identifier>
<dc:identifier opf:scheme="AMAZON">B00590YMHI</dc:identifier>
<dc:language>eng</dc:language>
<meta name="calibre:series" content="Old Series"/>
<meta name="calibre:series_index" content="9"/>
<meta name="calibre:timestamp" content="2014-05-13T19:00:18+00:00"/>
"""


def opf_of(book_bytes: bytes, tmp_path) -> str:
    path = tmp_path / "out.epub"
    path.write_bytes(book_bytes)
    with zipfile.ZipFile(path) as z:
        return z.read("OEBPS/package.opf").decode()


def epub3(tmp_path):
    return make_epub(tmp_path / "b.epub", metadata=EPUB3, unique_identifier="uid")


def test_epub3_reads_back_as_written(tmp_path):
    out = tmp_path / "out.epub"
    out.write_bytes(rewrite(epub3(tmp_path), META))
    back = read(out)
    assert back.title == META.title
    assert back.authors == META.authors
    assert (back.series, back.series_index) == ("The Stormlight Archive", "1")
    assert back.isbn == META.isbn
    assert back.date == META.date
    assert back.description == META.description
    assert back.genres == META.genres


def test_epub3_keeps_what_bookdrop_does_not_own(tmp_path):
    text = opf_of(rewrite(epub3(tmp_path), META), tmp_path)
    assert "All rights reserved" in text
    assert "schema:accessMode" in text
    assert "A Translator" in text and 'refines="#c2"' in text
    assert "urn:uuid:0b4f5a1e" in text
    assert "<dc:source>urn:isbn:9780374248529</dc:source>" in text


def test_epub3_removes_what_it_replaces_and_its_refinements(tmp_path):
    text = opf_of(rewrite(epub3(tmp_path), META), tmp_path)
    for gone in (
        "Old Title",
        "Old Author",
        "Old Series",
        'refines="#t"',
        'refines="#s"',
    ):
        assert gone not in text
    assert ">2009<" not in text
    assert "2021-08-05T17:30:56Z" not in text  # dcterms:modified moves on


def test_epub3_uses_only_epub3_forms(tmp_path):
    text = opf_of(rewrite(epub3(tmp_path), META), tmp_path)
    assert "opf:role" not in text and "opf:scheme" not in text
    assert 'property="role" scheme="marc:relators">aut<' in text
    assert 'property="identifier-type" scheme="onix:codelist5">15<' in text


def test_epub2_uses_the_forms_stump_reads(tmp_path):
    book = make_epub(tmp_path / "b.epub", metadata=EPUB2, version="2.0")
    text = opf_of(rewrite(book, META), tmp_path)
    assert re.search(r'<dc:identifier [^>]*opf:scheme="ISBN"[^>]*>9780765376671<', text)
    assert re.search(r'<dc:creator [^>]*opf:role="aut"[^>]*>Brandon Sanderson<', text)
    assert re.search(r'<meta [^>]*name="calibre:series" content="The Stormlight', text)
    assert "B00590YMHI" in text and "calibre:timestamp" in text
    assert "9780441015610" not in text and "Old Series" not in text


@pytest.mark.parametrize("version", ["2.0", "3.0"])
def test_prefixes_are_spelt_as_stump_matches_them(tmp_path, version):
    book = make_epub(tmp_path / "b.epub", metadata=EPUB2, version=version)
    text = opf_of(rewrite(book, META), tmp_path)
    assert not re.search(r"\bns\d+:", text)
    assert "<dc:title" in text and "<dc:subject" in text
    etree.fromstring(text.encode())


def test_only_the_opf_changes_and_mimetype_stays_first_and_stored(tmp_path):
    book = make_epub(tmp_path / "b.epub", metadata=EPUB2, version="2.0")
    out = tmp_path / "out.epub"
    out.write_bytes(rewrite(book, META))
    with zipfile.ZipFile(book) as a, zipfile.ZipFile(out) as b:
        assert a.namelist() == b.namelist()
        assert b.infolist()[0].filename == "mimetype"
        assert b.infolist()[0].compress_type == zipfile.ZIP_STORED
        changed = [n for n in a.namelist() if a.read(n) != b.read(n)]
    assert changed == ["OEBPS/package.opf"]


def test_an_empty_language_keeps_the_books_own(tmp_path):
    book = make_epub(tmp_path / "b.epub", metadata=EPUB2, version="2.0")
    meta = Metadata(title="T", authors=["A"])
    assert "<dc:language>eng</dc:language>" in opf_of(rewrite(book, meta), tmp_path)


def test_sidecar_is_calibre_shaped_and_reads_back(tmp_path):
    text = sidecar(META, cover=True)
    root = etree.fromstring(text)
    assert root.get("version") == "2.0"
    assert b'href="cover.jpg"' in text
    assert b'opf:scheme="ISBN"' in text and b'opf:scheme="uuid"' in text
    assert b"&lt;storms&gt;" in text
    assert b"<guide>" not in sidecar(META, cover=False)


@pytest.mark.parametrize(
    ("title", "language", "expected"),
    [
        ("The Way of Kings", "en", "Way of Kings, The"),
        ("A Memory Called Empire", "en-US", "Memory Called Empire, A"),
        ("An Instance of the Fingerpost", "", "Instance of the Fingerpost, An"),
        ("Theory of Everything", "en", "Theory of Everything"),
        ("The", "en", "The"),
        ("Die Verwandlung", "de", "Die Verwandlung"),
    ],
)
def test_title_sort(title, language, expected):
    assert title_sort(title, language) == expected


def test_the_packages_own_identifier_stays_even_as_an_isbn(tmp_path):
    own = '<dc:identifier id="pub">9780441015610</dc:identifier><dc:title>T</dc:title>'
    book = make_epub(
        tmp_path / "b.epub", metadata=own, version="2.0", unique_identifier="pub"
    )
    assert '<dc:identifier id="pub">9780441015610<' in opf_of(
        rewrite(book, META), tmp_path
    )
