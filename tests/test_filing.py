import io
from pathlib import PurePosixPath

import pytest
from conftest import make_epub
from PIL import Image

from bookdrop.drops import Drop
from bookdrop.filing import FilingError, jpeg, plan
from bookdrop.metadata import Metadata, read

META = Metadata(
    title="Dune Messiah", authors=["Frank Herbert"], series="Dune", series_index="2"
)


def png() -> bytes:
    out = io.BytesIO()
    Image.new("RGBA", (4, 6), (200, 10, 10, 128)).save(out, "PNG")
    return out.getvalue()


def drop_of(tmp_path, book_name: str, metadata: Metadata = META) -> Drop:
    return Drop(directory=tmp_path, book_name=book_name, metadata=metadata)


def test_an_epub_becomes_the_book_its_cover_and_its_sidecar(tmp_path):
    make_epub(
        tmp_path / "book.epub",
        title="Old",
        manifest="<item id='c' href='c.png' media-type='image/png' "
        "properties='cover-image'/>",
        files={"OEBPS/c.png": png()},
    )
    result = plan(drop_of(tmp_path, "book.epub"))

    assert result.directory == PurePosixPath("Frank Herbert/Dune/Dune Messiah")
    assert list(result.files) == ["Dune Messiah.epub", "cover.jpg", "metadata.opf"]
    written = tmp_path / "written.epub"
    written.write_bytes(result.files["Dune Messiah.epub"])
    assert read(written).title == "Dune Messiah"
    assert result.files["cover.jpg"][:3] == b"\xff\xd8\xff"
    assert b'href="cover.jpg"' in result.files["metadata.opf"]


def test_a_pdf_is_filed_as_it_came_with_its_sidecar(tmp_path):
    (tmp_path / "book.pdf").write_bytes(b"%PDF-1.7\nthe book")
    result = plan(drop_of(tmp_path, "book.pdf"))
    assert result.files["Dune Messiah.pdf"] == b"%PDF-1.7\nthe book"
    assert "cover.jpg" not in result.files
    assert b"<guide>" not in result.files["metadata.opf"]


def test_planning_writes_nothing(tmp_path):
    make_epub(tmp_path / "book.epub")
    before = sorted(p.name for p in tmp_path.iterdir())
    plan(drop_of(tmp_path, "book.epub"))
    assert sorted(p.name for p in tmp_path.iterdir()) == before


def test_a_jpeg_cover_is_kept_as_it_is():
    assert jpeg(b"\xff\xd8\xff\xe0 bytes", "image/jpeg") == b"\xff\xd8\xff\xe0 bytes"


@pytest.mark.parametrize(
    ("entries", "said"),
    [
        ({"mimetype": "application/epub+zip"}, "container.xml"),
        (
            {
                "mimetype": "application/epub+zip",
                "META-INF/container.xml": "<container/>",
            },
            "names no OPF",
        ),
        (
            {
                "mimetype": "application/epub+zip",
                "META-INF/container.xml": "<container><rootfile full-path='p.opf'/>"
                "</container>",
                "p.opf": "<package><not closed>",
            },
            "",
        ),
    ],
)
def test_a_book_it_cannot_read_is_a_filing_error(tmp_path, entries, said):
    import zipfile

    with zipfile.ZipFile(tmp_path / "book.epub", "w") as z:
        for name, data in entries.items():
            z.writestr(zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0)), data)
    with pytest.raises(
        FilingError, match=f"could not be prepared for filing: .*{said}"
    ):
        plan(drop_of(tmp_path, "book.epub"))
