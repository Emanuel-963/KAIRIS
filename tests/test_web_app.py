"""End-to-end tests for the local KAIRIS dashboard API."""

from __future__ import annotations

import io
import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from web_app import create_app


PROJECT_DIR = Path(__file__).resolve().parents[1]
FIXTURE = PROJECT_DIR / "tests" / "fixtures" / "synthetic_btlab.txt"


class WebAppTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="kairis_web_")
        self.root = Path(self.temporary.name)
        self.input_dir = self.root / "input"
        self.output_dir = self.root / "output"
        self.input_dir.mkdir()
        shutil.copy2(FIXTURE, self.input_dir / FIXTURE.name)
        self.config_path = self.root / "protocol_config.json"
        config = json.loads((PROJECT_DIR / "config" / "protocol_config.json").read_text(encoding="utf-8"))
        config["llm_enabled"] = False
        self.config_path.write_text(json.dumps(config), encoding="utf-8")
        self.app = create_app(self.input_dir, self.output_dir, self.config_path)
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.app.extensions["kairis_manager"].shutdown()
        self.temporary.cleanup()

    def test_dashboard_pipeline_and_watch_lifecycle(self) -> None:
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"KAIRIS", page.data)
        self.assertIn(b"llm-toggle", page.data)
        self.assertEqual(self.client.get("/health").get_json()["status"], "ok")

        started = self.client.post("/api/run")
        self.assertEqual(started.status_code, 200)
        self.assertTrue(started.get_json()["running"])

        deadline = time.monotonic() + 60
        status = None
        while time.monotonic() < deadline:
            status = self.client.get("/api/status").get_json()
            if not status["running"]:
                break
            time.sleep(0.25)
        self.assertIsNotNone(status)
        self.assertFalse(status["running"])
        self.assertEqual(status["exit_code"], 0)
        self.assertEqual(len(status["reports"]), 1)
        self.assertEqual(len(status["progress"]), 1)
        self.assertTrue(all(agent["state"] == "complete" for agent in status["progress"][0]["agents"].values()))

        report = self.client.get(status["reports"][0]["url"])
        self.assertEqual(report.status_code, 200)
        self.assertIn(b"KAIRIS", report.data)
        self.assertIn(b"Spectral Smoothness (local residue)", report.data)
        self.assertIn(b"n\xc3\xa3o \xc3\xa9 uma valida\xc3\xa7\xc3\xa3o integral de Kramers-Kronig", report.data)
        self.assertIn(b"Valida\xc3\xa7\xc3\xa3o linear Kramers-Kronig (Lin-KK)", report.data)
        self.assertIn(b"Res\xc3\xadduo normalizado Lin-KK", report.data)
        report.close()

        watched = self.client.post("/api/watch/start").get_json()
        self.assertTrue(watched["running"])
        self.assertEqual(watched["mode"], "watch")
        stopped = self.client.post("/api/stop").get_json()
        self.assertFalse(stopped["running"])

    def test_upload_validation_and_unique_names(self) -> None:
        payload = FIXTURE.read_bytes()
        response = self.client.post(
            "/api/upload",
            data={"files": [(io.BytesIO(payload), "sample.txt"), (io.BytesIO(payload), "sample.txt")]},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["saved"], ["sample.txt", "sample_1.txt"])

        csv_response = self.client.post(
            "/api/upload",
            data={"files": (io.BytesIO(b"not eis"), "sample.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(csv_response.status_code, 200)
        self.assertEqual(csv_response.get_json()["saved"], ["sample.csv"])

        rejected = self.client.post(
            "/api/upload",
            data={"files": (io.BytesIO(b"not eis"), "sample.xlsx")},
            content_type="multipart/form-data",
        )
        self.assertEqual(rejected.status_code, 400)

    def test_llm_switch_is_persistent_and_available_while_watching(self) -> None:
        initial = self.client.get("/api/status").get_json()
        self.assertFalse(initial["llm_enabled"])

        enabled = self.client.post("/api/llm", json={"enabled": True})
        self.assertEqual(enabled.status_code, 200)
        self.assertTrue(enabled.get_json()["llm_enabled"])

        watched = self.client.post("/api/watch/start").get_json()
        self.assertTrue(watched["running"])
        disabled = self.client.post("/api/llm", json={"enabled": False}).get_json()
        self.assertFalse(disabled["llm_enabled"])
        self.client.post("/api/stop")

        control = json.loads((self.output_dir / "runtime_control.json").read_text(encoding="utf-8"))
        self.assertIs(control["llm_enabled"], False)


if __name__ == "__main__":
    unittest.main()
