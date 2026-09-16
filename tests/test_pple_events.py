"""Unit tests for the internal event bus (docs/final.md Phase 28)."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, patch

import pandas as pd

from pple.core import events
from pple.core.events import Events


class EventBusTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(events.clear_subscribers)

    def test_publish_notifies_subscriber(self):
        received = []
        events.subscribe(Events.EQUIPMENT_CREATED, lambda event, payload: received.append((event, payload)))
        events.publish(Events.EQUIPMENT_CREATED, asset_id="AST-1")
        self.assertEqual(received, [(Events.EQUIPMENT_CREATED, {"asset_id": "AST-1"})])

    def test_publish_with_no_subscribers_does_not_raise(self):
        events.publish(Events.ANALYSIS_STARTED, equipment="X")

    def test_subscribe_rejects_unknown_event(self):
        with self.assertRaises(ValueError):
            events.subscribe("not.a.real.event", lambda *a: None)

    def test_publish_unknown_event_is_logged_not_raised(self):
        events.publish("not.a.real.event")

    def test_failing_subscriber_does_not_break_others(self):
        received = []

        def bad_handler(event, payload):
            raise RuntimeError("boom")

        events.subscribe(Events.WORKORDER_REQUESTED, bad_handler)
        events.subscribe(Events.WORKORDER_REQUESTED, lambda event, payload: received.append(event))
        events.publish(Events.WORKORDER_REQUESTED, equipment="X")
        self.assertEqual(received, [Events.WORKORDER_REQUESTED])

    def test_unsubscribe_stops_delivery(self):
        received = []
        handler = lambda event, payload: received.append(event)
        events.subscribe(Events.DIAGNOSTIC_CREATED, handler)
        events.unsubscribe(Events.DIAGNOSTIC_CREATED, handler)
        events.publish(Events.DIAGNOSTIC_CREATED, equipment="X")
        self.assertEqual(received, [])

    def test_all_events_constant_matches_spec(self):
        self.assertEqual(
            events.ALL_EVENTS,
            {
                "equipment.created",
                "equipment.updated",
                "measurement.uploaded",
                "analysis.started",
                "analysis.completed",
                "analysis.failed",
                "diagnostic.created",
                "severity.changed",
                "recommendation.created",
                "workorder.requested",
            },
        )


class WiredPublisherTests(unittest.TestCase):
    """Confirm the call sites documented in pple/core/events.py actually publish."""

    def setUp(self):
        self.addCleanup(events.clear_subscribers)

    def _probe(self, event_name):
        seen = []
        events.subscribe(event_name, lambda event, payload: seen.append(payload))
        return seen

    def test_diagnose_from_inputs_publishes_lifecycle_events(self):
        from pple.application import DiagnoseEquipmentUseCase

        started = self._probe(Events.ANALYSIS_STARTED)
        completed = self._probe(Events.ANALYSIS_COMPLETED)
        created = self._probe(Events.DIAGNOSTIC_CREATED)

        mock_fusion = MagicMock()
        mock_fusion.run_full_fusion.return_value = {"health_index": 90.0, "health_status": "HEALTHY"}
        use_case = DiagnoseEquipmentUseCase(fusion_agent=mock_fusion, asset_graph=MagicMock())
        use_case.diagnose_from_inputs(equipment="BFP 1A")

        self.assertEqual(len(started), 1)
        self.assertEqual(len(completed), 1)
        self.assertEqual(len(created), 1)

    def test_diagnose_from_inputs_publishes_failure_event_and_still_raises(self):
        from pple.application import DiagnoseEquipmentUseCase

        failed = self._probe(Events.ANALYSIS_FAILED)
        mock_fusion = MagicMock()
        mock_fusion.run_full_fusion.side_effect = RuntimeError("boom")
        use_case = DiagnoseEquipmentUseCase(fusion_agent=mock_fusion, asset_graph=MagicMock())
        with self.assertRaises(RuntimeError):
            use_case.diagnose_from_inputs(equipment="BFP 1A")
        self.assertEqual(len(failed), 1)

    def test_upsert_asset_publishes_created_then_updated(self):
        from src import asset_registry

        created = self._probe(Events.EQUIPMENT_CREATED)
        updated = self._probe(Events.EQUIPMENT_UPDATED)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(asset_registry, "get_data_path", side_effect=lambda *parts: str(root.joinpath(*parts))):
                asset_registry.upsert_asset({"asset_id": "AST-EVT", "name": "Test Pump"})
                self.assertEqual(len(created), 1)
                self.assertEqual(len(updated), 0)

                asset_registry.upsert_asset({"asset_id": "AST-EVT", "name": "Test Pump v2"})
                self.assertEqual(len(created), 1)
                self.assertEqual(len(updated), 1)

    def test_generate_cbm_work_order_publishes_once_not_on_duplicate(self):
        from src import work_orders

        requested = self._probe(Events.WORKORDER_REQUESTED)
        temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        temp_file.close()
        os.environ["WORK_ORDERS_FILE"] = temp_file.name
        self.addCleanup(os.environ.pop, "WORK_ORDERS_FILE", None)
        self.addCleanup(os.remove, temp_file.name)

        work_orders.generate_cbm_work_order(equipment="EVT PUMP 1", domain="Vibrasi", severity="CRITICAL")
        self.assertEqual(len(requested), 1)

        # Same equipment+domain with an open WO already exists -> returns it, no new event.
        work_orders.generate_cbm_work_order(equipment="EVT PUMP 1", domain="Vibrasi", severity="CRITICAL")
        self.assertEqual(len(requested), 1)

    def test_commit_batch_publishes_measurement_uploaded(self):
        from src import domain_ingest as ingest

        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(os.environ, {"MCSA_DATA_DIR": temporary}):
                uploaded = self._probe(Events.MEASUREMENT_UPLOADED)
                frame = pd.DataFrame([
                    {"equipment": "CWP 1A", "unit_name": "UNIT 1", "test_date": "2026-05-01", "overall_rms": 3.2},
                ])
                content = frame.to_csv(index=False).encode("utf-8")
                preview = ingest.preview_upload("VIBRASI", "uji.csv", content)
                batch_path, _ = ingest.create_batch("VIBRASI", "uji.csv", content, preview)
                ingest.commit_batch("VIBRASI", batch_path, preview)
                self.assertEqual(len(uploaded), 1)


if __name__ == "__main__":
    unittest.main()
