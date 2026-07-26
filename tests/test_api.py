import tempfile
import unittest
from pathlib import Path

from flight_overlay.app import create_app


class ApiTests(unittest.TestCase):
    def test_pages_and_api_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(
                settings_path=Path(directory) / "settings.json",
                start_services=False,
            )
            client = app.test_client()
            self.assertEqual(client.get("/").status_code, 200)
            self.assertEqual(client.get("/settings").status_code, 200)
            health = client.get("/healthz")
            self.assertEqual(health.status_code, 200)
            self.assertEqual(health.json["version"], "2.0.1")

            settings = client.get("/api/settings").json
            self.assertEqual(len(settings["themes"]), 15)
            self.assertEqual(len(settings["aircraftIcons"]), 6)
            settings["settings"]["appearance"]["theme"] = "aurora"
            saved = client.put("/api/settings", json=settings["settings"])
            self.assertEqual(saved.status_code, 200)
            self.assertEqual(
                saved.json["settings"]["appearance"]["theme"], "aurora"
            )
            data = client.get("/api/data")
            self.assertEqual(data.status_code, 200)
            self.assertTrue(
                {"telemetry", "connection", "phase", "integrations"}
                <= set(data.json)
            )

    def test_settings_reject_non_object_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(
                settings_path=Path(directory) / "settings.json",
                start_services=False,
            )
            response = app.test_client().put("/api/settings", json=["invalid"])
            self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
