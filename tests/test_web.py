from conftest import ACSM, drm_epub, make_epub
from fastapi.testclient import TestClient

from bookdrop.config import Settings
from bookdrop.web import create_app


def test_dry_run_unless_disabled(monkeypatch):
    monkeypatch.delenv("BOOKDROP_DRY_RUN", raising=False)
    assert Settings().dry_run is True


def test_dry_run_disabled_explicitly(monkeypatch):
    monkeypatch.setenv("BOOKDROP_DRY_RUN", "false")
    assert Settings().dry_run is False


def test_healthz_reports_mode():
    client = TestClient(create_app(Settings(dry_run=True)))
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "dry_run": True}


def test_index_states_dry_run():
    client = TestClient(create_app(Settings(dry_run=True)))
    assert "nothing in the library is changed" in client.get("/").text


def test_drop_prepares_a_drm_free_epub(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", adept_dir=tmp_path / "adept")
    client = TestClient(create_app(settings))
    epub = make_epub(tmp_path / "book.epub").read_bytes()

    response = client.post("/drop", files={"file": ("book.epub", epub)})

    assert response.status_code == 200
    assert "<b>A Synthetic Book</b>: EPUB" in response.text
    assert "It arrived DRM-free." in response.text
    (drop,) = (tmp_path / "data" / "drops").iterdir()
    assert [p.name for p in drop.iterdir()] == ["book.epub"]


def test_drop_refuses_and_keeps_nothing(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", adept_dir=tmp_path / "adept")
    client = TestClient(create_app(settings))

    response = client.post("/drop", files={"file": ("notes.txt", b"plain text")})

    assert response.status_code == 422
    assert "Only an .acsm, an EPUB or a PDF" in response.text
    assert list((tmp_path / "data" / "drops").iterdir()) == []


def test_file_picker_filters_nothing():
    # iOS refuses .acsm files from a picker that names accepted types.
    client = TestClient(create_app(Settings(dry_run=True)))
    assert "accept=" not in client.get("/").text


def test_drop_of_an_acsm_reports_the_book_and_what_was_done(
    tmp_path, tools, adept_dir, monkeypatch
):
    monkeypatch.setenv("STUB_FULFILLED", str(drm_epub(tmp_path / "drm.epub")))
    monkeypatch.setenv(
        "STUB_STRIPPED", str(make_epub(tmp_path / "clean.epub", title="Real Title"))
    )
    settings = Settings(data_dir=tmp_path / "data", adept_dir=adept_dir)
    client = TestClient(create_app(settings))

    response = client.post("/drop", files={"file": ("URLLink.acsm", ACSM)})

    assert "<b>Real Title</b>: EPUB" in response.text
    assert "Downloaded from the store, DRM removed." in response.text
    assert "URLLink" not in response.text


def test_drop_without_a_title_names_the_upload(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", adept_dir=tmp_path / "adept")
    client = TestClient(create_app(settings))
    epub = make_epub(tmp_path / "b.epub", title=None).read_bytes()

    response = client.post("/drop", files={"file": ("mine.epub", epub)})

    assert "<b>mine.epub</b>: EPUB" in response.text
