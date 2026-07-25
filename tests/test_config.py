from pathlib import Path

from flight_overlay.config import DEFAULT_SETTINGS, SettingsStore, THEMES, validate_settings


def test_defaults_expose_fifteen_themes():
    assert len(THEMES) == 15
    assert DEFAULT_SETTINGS["appearance"]["theme"] == "midnight"
    assert DEFAULT_SETTINGS["appearance"]["transparency"] == 30


def test_validation_clamps_values_and_rejects_unknown_choices():
    result = validate_settings(
        {
            "appearance": {
                "theme": "not-a-theme",
                "aircraftIcon": "balloon",
                "transparency": 500,
                "scale": 2,
            },
            "layout": {
                "primaryMetrics": ["airspeed", "airspeed", "unknown"],
                "secondaryMetrics": ["altitude"],
            },
        }
    )
    assert result["appearance"]["theme"] == "midnight"
    assert result["appearance"]["aircraftIcon"] == "airliner"
    assert result["appearance"]["transparency"] == 100
    assert result["appearance"]["scale"] == 60
    assert result["layout"]["primaryMetrics"] == ["airspeed"]
    assert len(
        result["layout"]["primaryMetrics"] + result["layout"]["secondaryMetrics"]
    ) == 9


def test_store_round_trip_and_reset(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.json")
    settings = store.get()
    settings["appearance"]["theme"] = "aurora"
    store.save(settings)
    assert SettingsStore(tmp_path / "settings.json").get()["appearance"]["theme"] == "aurora"
    assert store.reset()["appearance"]["theme"] == "midnight"
