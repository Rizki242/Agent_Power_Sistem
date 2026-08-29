import os
import tempfile
import unittest

from src.domain_overrides import DomainOverrideStore


class DomainOverrideStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmpdir.name, "overrides.json")
        self.store = DomainOverrideStore(self.path)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_missing_file_returns_empty(self):
        self.assertEqual(self.store.all(), {})
        self.assertIsNone(self.store.get("X-1"))

    def test_set_then_get_round_trips(self):
        self.store.set("X-1", {"name": "Test", "value": 42})
        self.assertEqual(self.store.get("X-1"), {"name": "Test", "value": 42})
        self.assertEqual(self.store.all(), {"X-1": {"name": "Test", "value": 42}})

    def test_set_replaces_existing_entry(self):
        self.store.set("X-1", {"value": 1})
        self.store.set("X-1", {"value": 2})
        self.assertEqual(self.store.get("X-1"), {"value": 2})

    def test_multiple_records_independent(self):
        self.store.set("X-1", {"value": 1})
        self.store.set("X-2", {"value": 2})
        self.assertEqual(self.store.get("X-1"), {"value": 1})
        self.assertEqual(self.store.get("X-2"), {"value": 2})
        self.assertEqual(len(self.store.all()), 2)

    def test_persists_across_store_instances(self):
        self.store.set("X-1", {"value": 1})
        other = DomainOverrideStore(self.path)
        self.assertEqual(other.get("X-1"), {"value": 1})

    def test_corrupt_file_is_treated_as_empty(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{not valid json")
        self.assertEqual(self.store.all(), {})


if __name__ == "__main__":
    unittest.main()
