import importlib.util
import tempfile
import time
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "deploy" / "role_status.py"
SPEC = importlib.util.spec_from_file_location("role_status", MODULE_PATH)
role_status = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(role_status)


class RoleStatusContractTest(unittest.TestCase):
    def test_duplicate_component_is_unhealthy(self):
        component = {"state": "unhealthy", "count": 2}
        lifecycle = {"state": "ready"}
        self.assertEqual(role_status.overall([component], lifecycle), "unhealthy")

    def test_startup_grace_relabels_missing(self):
        component = {"state": "missing", "ok": False}
        lifecycle = {"state": "starting", "age_s": 2}
        result = role_status.normalize_starting(component, lifecycle)
        self.assertEqual(result["state"], "starting")
        self.assertFalse(result["ok"])

    def test_intentional_stop_is_distinct(self):
        lifecycle = {"state": "stopped"}
        components = [{"state": "missing"}, {"state": "unreachable"}]
        self.assertEqual(role_status.overall(components, lifecycle), "stopped")

    def test_lifecycle_state_is_read_from_persistent_directory(self):
        old_role = role_status.ROLE
        role_status.ROLE = "server_pc"
        try:
            with tempfile.TemporaryDirectory() as directory:
                timestamp = int(time.time())
                Path(directory, "server_pc.state").write_text(f"ready|{timestamp}|ok\n")
                result = role_status.state_record(directory)
                self.assertEqual(result["state"], "ready")
                self.assertEqual(result["message"], "ok")
        finally:
            role_status.ROLE = old_role

    def test_ai_server_component_accepts_fresh_relay_status(self):
        payload = {
            "server_pc": {
                "fetch": {
                    "state": "ready",
                    "source": "relay",
                    "status": 200,
                    "relay_age_s": 1,
                    "error": "using relay",
                }
            }
        }
        result = role_status.dashboard_server_component(payload, {"state": "ready", "age_s": 1})
        self.assertEqual(result["state"], "ready")
        self.assertTrue(result["ok"])
        self.assertEqual(result["source"], "relay")

    def test_ai_server_component_reports_missing_dashboard_payload(self):
        result = role_status.dashboard_server_component({}, {"state": "ready", "age_s": 1})
        self.assertEqual(result["state"], "unreachable")
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
