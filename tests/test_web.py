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
