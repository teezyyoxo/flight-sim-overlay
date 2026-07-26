from flight_overlay.app import create_app
from flight_overlay.version import __version__


def test_pages_and_health(tmp_path):
    app = create_app(settings_path=tmp_path / "settings.json", start_services=False)
    client = app.test_client()
    assert client.get("/").status_code == 200
    assert client.get("/settings").status_code == 200
    health = client.get("/healthz").get_json()
    assert health["ok"] is True
    assert health["version"] == "2.0.2" == __version__
    data = client.get("/api/data").get_json()
    assert data["progress"] is None
    assert data["progressSource"] == "unavailable"
    assert data["phase"]["label"] == "At the gate"


def test_settings_api_persists_validated_values(tmp_path):
    path = tmp_path / "settings.json"
    app = create_app(settings_path=path, start_services=False)
    client = app.test_client()
    settings = client.get("/api/settings").get_json()["settings"]
    settings["appearance"]["theme"] = "aurora"
    settings["appearance"]["transparency"] = 44
    response = client.put("/api/settings", json=settings)
    assert response.status_code == 200
    saved = response.get_json()["settings"]
    assert saved["appearance"]["theme"] == "aurora"
    assert saved["appearance"]["transparency"] == 44
    assert path.exists()


def test_aircraft_assets_are_intrinsically_right_facing():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    for asset in (root / "static" / "images" / "aircraft").glob("*.svg"):
        assert "rotate(90" in asset.read_text(encoding="utf-8"), asset.name
