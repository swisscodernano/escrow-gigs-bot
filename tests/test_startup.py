from fastapi.testclient import TestClient

def test_app_startup_without_bot(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "")
    from app.app import app
    c = TestClient(app)
    r = c.get("/")
    assert r.status_code in (200, 404)
