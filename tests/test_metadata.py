import zipfile

from conftest import make_epub

from bookdrop.metadata import title


def test_title_from_the_opf(tmp_path):
    assert title(make_epub(tmp_path / "b.epub", title="The Title")) == "The Title"


def test_no_title(tmp_path):
    assert title(make_epub(tmp_path / "b.epub", title=None)) is None


def test_no_container_or_not_a_zip(tmp_path):
    bare = tmp_path / "bare.epub"
    with zipfile.ZipFile(bare, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype", (2020, 1, 1, 0, 0, 0)), "x")
    assert title(bare) is None
    pdf = tmp_path / "b.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    assert title(pdf) is None
