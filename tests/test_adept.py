import pytest
from conftest import ACSM, drm_epub, make_epub

from bookdrop.adept import Refused, encrypted, kind, prepare

AES = "http://www.w3.org/2001/04/xmlenc#aes128-cbc"
FONT = "http://www.idpf.org/2008/embedding"


@pytest.fixture
def out_dir(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    return out


def test_kind_by_content_not_name(tmp_path):
    acsm = tmp_path / "book.epub"
    acsm.write_text(ACSM)
    assert kind(acsm) == "acsm"
    assert kind(make_epub(tmp_path / "book.acsm")) == "epub"
    pdf = tmp_path / "book"
    pdf.write_bytes(b"%PDF-1.7\n")
    assert kind(pdf) == "pdf"


@pytest.mark.parametrize(
    "content",
    [b"plain text", b"<?xml version='1.0'?><other/>", b"PK\x03\x04 not really"],
)
def test_kind_refuses_anything_else(tmp_path, content):
    path = tmp_path / "upload"
    path.write_bytes(content)
    with pytest.raises(Refused):
        kind(path)


@pytest.mark.parametrize(
    ("rights", "algorithms", "expected"),
    [
        (False, (), False),
        (False, (FONT,), False),
        (False, (FONT, AES), True),
        (True, (), True),
    ],
)
def test_encrypted_epub(tmp_path, rights, algorithms, expected):
    epub = make_epub(tmp_path / "b.epub", rights=rights, algorithms=algorithms)
    assert encrypted(epub, "epub") is expected


def test_encrypted_pdf(tmp_path):
    pdf = tmp_path / "b.pdf"
    pdf.write_bytes(b"%PDF-1.7\ntrailer << /Encrypt 5 0 R >>")
    assert encrypted(pdf, "pdf")
    pdf.write_bytes(b"%PDF-1.7\ntrailer << /Root 1 0 R >>")
    assert not encrypted(pdf, "pdf")


def test_acsm_is_fulfilled_and_stripped(
    tmp_path, out_dir, tools, adept_dir, monkeypatch
):
    monkeypatch.setenv("STUB_FULFILLED", str(drm_epub(tmp_path / "drm.epub")))
    monkeypatch.setenv("STUB_STRIPPED", str(make_epub(tmp_path / "clean.epub")))
    acsm = tmp_path / "URLLink.acsm"
    acsm.write_text(ACSM)

    prepared = prepare(acsm, out_dir, adept_dir)

    assert prepared.book == out_dir / "book.epub"
    assert not encrypted(prepared.book, "epub")
    assert prepared.preparation == "Downloaded from the store, DRM removed."


def test_acsm_the_store_sent_drm_free(tmp_path, out_dir, tools, adept_dir, monkeypatch):
    monkeypatch.setenv("STUB_FULFILLED", str(make_epub(tmp_path / "free.epub")))
    monkeypatch.delenv("STUB_STRIPPED", raising=False)
    acsm = tmp_path / "URLLink.acsm"
    acsm.write_text(ACSM)

    prepared = prepare(acsm, out_dir, adept_dir)

    assert prepared.preparation == "Downloaded from the store, which sent it DRM-free."


def test_read_only_key_is_never_written(
    tmp_path, out_dir, tools, adept_dir, monkeypatch
):
    monkeypatch.setenv("STUB_FULFILLED", str(drm_epub(tmp_path / "drm.epub")))
    monkeypatch.setenv("STUB_STRIPPED", str(make_epub(tmp_path / "clean.epub")))
    acsm = tmp_path / "URLLink.acsm"
    acsm.write_text(ACSM)

    prepare(acsm, out_dir, adept_dir)

    assert (adept_dir / "activation.xml").read_text() == "activation.xml"


def test_still_encrypted_after_stripping_is_refused(
    tmp_path, out_dir, tools, adept_dir, monkeypatch
):
    monkeypatch.setenv("STUB_FULFILLED", str(drm_epub(tmp_path / "drm.epub")))
    monkeypatch.setenv("STUB_STRIPPED", str(drm_epub(tmp_path / "still.epub")))
    acsm = tmp_path / "URLLink.acsm"
    acsm.write_text(ACSM)

    with pytest.raises(Refused, match="could not be removed"):
        prepare(acsm, out_dir, adept_dir)


def test_tool_failure_is_refused_with_its_message(
    tmp_path, out_dir, tools, adept_dir, monkeypatch
):
    monkeypatch.delenv("STUB_FULFILLED", raising=False)
    acsm = tmp_path / "URLLink.acsm"
    acsm.write_text(ACSM)

    with pytest.raises(Refused, match="acsmdownloader failed: .*told to fail"):
        prepare(acsm, out_dir, adept_dir)


def test_drm_free_epub_needs_no_tools(tmp_path, out_dir, adept_dir, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path / "nothing-here"))
    prepared = prepare(make_epub(tmp_path / "upload"), out_dir, adept_dir)
    assert prepared.book == out_dir / "book.epub"
    assert not encrypted(prepared.book, "epub")
    assert prepared.preparation == "It arrived DRM-free."


def test_encrypted_epub_upload_is_stripped(
    tmp_path, out_dir, tools, adept_dir, monkeypatch
):
    monkeypatch.setenv("STUB_STRIPPED", str(make_epub(tmp_path / "clean.epub")))
    prepared = prepare(drm_epub(tmp_path / "upload"), out_dir, adept_dir)
    assert not encrypted(prepared.book, "epub")
    assert prepared.preparation == "DRM removed."


def test_a_tool_that_hangs_is_refused(tmp_path, out_dir, tools, adept_dir, monkeypatch):
    (tools / "acsmdownloader").write_text("#!/bin/sh\nsleep 5\n")
    monkeypatch.setattr("bookdrop.adept.TOOL_TIMEOUT", 0.2)
    acsm = tmp_path / "URLLink.acsm"
    acsm.write_text(ACSM)
    with pytest.raises(Refused, match="did not finish within 0.2 seconds"):
        prepare(acsm, out_dir, adept_dir)
