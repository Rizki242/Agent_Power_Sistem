import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from pple.core import audit
from pple.engineering.equipment_modules import EquipmentModuleStore


class AuditRecordTests(unittest.TestCase):
    """docs/final.md Phase 29: WHO / WHAT / WHEN / OLD / NEW / SOURCE."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self._tmpdir, "audit", "audit_log.jsonl")
        self.addCleanup(shutil.rmtree, self._tmpdir, True)

    def _lines(self):
        with open(self.path, encoding="utf-8") as fp:
            return [json.loads(line) for line in fp if line.strip()]

    def test_record_change_writes_all_six_columns(self):
        audit.record_change(
            entity="CWP-1A",
            field="rated_speed",
            old_value="980 RPM",
            new_value="985 RPM",
            actor="Engineer",
            source=audit.SOURCE_CLI,
            path=self.path,
        )
        (event,) = self._lines()
        self.assertEqual(event["who"], "Engineer")
        self.assertEqual(event["entity"], "CWP-1A")
        self.assertEqual(event["field"], "rated_speed")
        self.assertEqual(event["old_value"], "980 RPM")
        self.assertEqual(event["new_value"], "985 RPM")
        self.assertEqual(event["source"], "CLI")
        self.assertTrue(event["when"])

    def test_log_is_append_only(self):
        for speed in ("981", "982", "983"):
            audit.record_change("CWP-1A", "rated_speed", "980", speed, path=self.path)
        self.assertEqual(len(self._lines()), 3)

    def test_actor_precedence_explicit_over_env(self):
        with patch.dict(os.environ, {audit.ACTOR_ENV: "dari-env"}):
            self.assertEqual(audit.resolve_actor("eksplisit"), "eksplisit")
            self.assertEqual(audit.resolve_actor(None), "dari-env")

    def test_actor_falls_back_to_os_user(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(audit.ACTOR_ENV, None)
            self.assertTrue(audit.resolve_actor(None))

    def test_unserialisable_value_is_stored_as_text(self):
        audit.record_change("CWP-1A", "threshold", object(), {"a": 1}, path=self.path)
        (event,) = self._lines()
        self.assertIsInstance(event["old_value"], str)
        self.assertIsInstance(event["new_value"], str)

    def test_write_failure_does_not_raise(self):
        # Parent adalah berkas, bukan folder: makedirs gagal. Operasi pemanggil
        # tetap harus jalan (fail-open), lihat docstring pple/core/audit.py.
        blocker = os.path.join(self._tmpdir, "bukan-folder")
        with open(blocker, "w", encoding="utf-8") as fp:
            fp.write("x")
        event = audit.record_change(
            "CWP-1A", "x", 1, 2, path=os.path.join(blocker, "audit.jsonl")
        )
        self.assertEqual(event["entity"], "CWP-1A")


class AuditReadTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self._tmpdir, "audit.jsonl")
        self.addCleanup(shutil.rmtree, self._tmpdir, True)
        audit.record_change("CWP-1A", "module:dga", "enabled", "disabled",
                            actor="a", source=audit.SOURCE_CLI, path=self.path)
        audit.record_change("CWP-2B", "module:vibration", "enabled", "disabled",
                            actor="b", source=audit.SOURCE_API, path=self.path)

    def test_missing_file_returns_empty(self):
        self.assertEqual(audit.read_events(path=os.path.join(self._tmpdir, "kosong.jsonl")), [])

    def test_newest_event_first(self):
        events = audit.read_events(path=self.path)
        self.assertEqual(events[0]["entity"], "CWP-2B")

    def test_limit_applies_after_ordering(self):
        events = audit.read_events(limit=1, path=self.path)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["entity"], "CWP-2B")

    def test_filter_by_entity_and_source(self):
        self.assertEqual(len(audit.read_events(entity="CWP-1A", path=self.path)), 1)
        self.assertEqual(len(audit.read_events(source="api", path=self.path)), 1)
        self.assertEqual(len(audit.read_events(entity="TIDAK-ADA", path=self.path)), 0)

    def test_corrupt_line_is_skipped_not_fatal(self):
        with open(self.path, "a", encoding="utf-8") as fp:
            fp.write("{bukan json}\n")
        self.assertEqual(len(audit.read_events(path=self.path)), 2)

    def test_describe_event_is_readable(self):
        summary = audit.describe_event(audit.read_events(path=self.path)[0])
        self.assertIn("CWP-2B", summary)
        self.assertIn("API", summary)


class EquipmentModuleAuditTests(unittest.TestCase):
    """Override modul adalah titik perubahan konfigurasi pertama yang diaudit."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self._tmpdir, True)
        self.audit_path = os.path.join(self._tmpdir, "audit.jsonl")
        self.store = EquipmentModuleStore(os.path.join(self._tmpdir, "overrides.json"))
        patcher = patch.object(audit, "default_log_path", lambda: self.audit_path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_disable_is_recorded(self):
        self.store.remove_module("CWP-1A", "dga", actor="Engineer", source=audit.SOURCE_CLI)
        (event,) = audit.read_events(path=self.audit_path)
        self.assertEqual(event["entity"], "CWP-1A")
        self.assertEqual(event["field"], "module:dga")
        self.assertEqual(event["old_value"], "enabled")
        self.assertEqual(event["new_value"], "disabled")
        self.assertEqual(event["who"], "Engineer")
        self.assertEqual(event["source"], "CLI")

    def test_re_enable_records_the_reverse(self):
        self.store.remove_module("CWP-1A", "dga")
        self.store.add_module("CWP-1A", "dga")
        events = audit.read_events(path=self.audit_path)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["old_value"], "disabled")
        self.assertEqual(events[0]["new_value"], "enabled")

    def test_no_op_is_not_audited(self):
        # Sudah enabled secara default; mengaktifkan lagi bukan perubahan.
        self.store.add_module("CWP-1A", "dga")
        self.assertEqual(audit.read_events(path=self.audit_path), [])

        self.store.remove_module("CWP-1A", "dga")
        self.store.remove_module("CWP-1A", "dga")
        self.assertEqual(len(audit.read_events(path=self.audit_path)), 1)

    def test_override_still_applies_after_auditing(self):
        self.store.remove_module("CWP-1A", "dga")
        self.assertFalse(self.store.is_enabled("CWP-1A", "dga"))
        self.assertTrue(self.store.is_enabled("CWP-1A", "vibration"))


if __name__ == "__main__":
    unittest.main()
