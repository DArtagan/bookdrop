from conftest import make_epub
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
    assert "DRM-free EPUB" in response.text
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
