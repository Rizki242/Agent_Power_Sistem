"""Unit tests for PPLE Phase 4 structured logging framework."""

import json
import logging
import unittest
from io import StringIO

from pple.core.logging import (
    JSONFormatter,
    correlation_id_var,
    get_correlation_id,
    get_logger,
    log_diagnosis,
    log_event,
    log_fallback,
    log_ingest,
    log_report_generation,
    set_correlation_id,
)


class StructuredLoggingTests(unittest.TestCase):
    """Test JSON formatting, correlation propagation, and domain event helpers."""

    def setUp(self):
        self.stream = StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.handler.setFormatter(JSONFormatter())
        self.logger = logging.getLogger("test_logger_pple")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.handler)
        # Reset correlation ID before each test
        set_correlation_id(None)

    def tearDown(self):
        self.logger.removeHandler(self.handler)
        set_correlation_id(None)

    def test_json_formatter_standard_record(self):
        self.logger.info("Test simple log")
        output = self.stream.getvalue().strip()
        data = json.loads(output)

        self.assertEqual(data.get("message"), "Test simple log")
        self.assertEqual(data.get("level"), "INFO")
        self.assertEqual(data.get("logger"), "test_logger_pple")
        self.assertIn("timestamp", data)
        self.assertIsNone(data.get("correlation_id"))

    def test_correlation_id_propagation_in_log(self):
        set_correlation_id("req-uuid-1234-abcd")
        self.assertEqual(get_correlation_id(), "req-uuid-1234-abcd")

        self.logger.info("Correlated message")
        output = self.stream.getvalue().strip()
        data = json.loads(output)

        self.assertEqual(data.get("correlation_id"), "req-uuid-1234-abcd")
        self.assertEqual(data.get("message"), "Correlated message")

    def test_structured_extra_payload(self):
        set_correlation_id("trace-999")
        self.logger.info(
            "Diagnostic performed",
            extra={"structured": {"equipment": "2A1", "health_index": 88.5}},
        )
        output = self.stream.getvalue().strip()
        data = json.loads(output)

        self.assertEqual(data.get("correlation_id"), "trace-999")
        self.assertEqual(data.get("equipment"), "2A1")
        self.assertEqual(data.get("health_index"), 88.5)

    def test_log_event_helper(self):
        logger = get_logger("pple.audit")
        logger.addHandler(self.handler)
        try:
            set_correlation_id("corr-evt-001")
            log_event(
                event="custom_audit",
                logger_name="pple.audit",
                user="engineer_1",
                action="approve_report",
            )
            output = self.stream.getvalue().strip()
            data = json.loads(output)

            self.assertEqual(data.get("event"), "custom_audit")
            self.assertEqual(data.get("user"), "engineer_1")
            self.assertEqual(data.get("action"), "approve_report")
            self.assertEqual(data.get("correlation_id"), "corr-evt-001")
        finally:
            logger.removeHandler(self.handler)

    def test_domain_event_helpers(self):
        loggers_to_attach = [
            get_logger("pple.ingest"),
            get_logger("pple.diagnosis"),
            get_logger("pple.reports"),
            get_logger("pple.fallback"),
        ]
        for l in loggers_to_attach:
            l.addHandler(self.handler)

        try:
            # 1. log_ingest
            log_ingest(domain="DGA", file_name="sample.xlsx", status="SUCCESS", record_count=12)
            # 2. log_diagnosis
            log_diagnosis(equipment="PA FAN 2A", health_index=91.4, health_status="HEALTHY", duration_ms=45.2)
            # 3. log_report_generation
            log_report_generation(report_id="RPT-001", equipment="PA FAN 2A", status="SUCCESS")
            # 4. log_fallback
            log_fallback(component="rag_engine", reason="faiss missing", fallback_used="keyword_retriever")

            lines = [json.loads(line) for line in self.stream.getvalue().strip().split("\n") if line]
            self.assertEqual(len(lines), 4)

            self.assertEqual(lines[0]["event"], "data_ingest")
            self.assertEqual(lines[0]["domain"], "DGA")
            self.assertEqual(lines[0]["record_count"], 12)

            self.assertEqual(lines[1]["event"], "diagnostic_fusion")
            self.assertEqual(lines[1]["equipment"], "PA FAN 2A")
            self.assertEqual(lines[1]["health_index"], 91.4)
            self.assertEqual(lines[1]["health_status"], "HEALTHY")

            self.assertEqual(lines[2]["event"], "report_generation")
            self.assertEqual(lines[2]["report_id"], "RPT-001")

            self.assertEqual(lines[3]["event"], "provider_fallback")
            self.assertEqual(lines[3]["component"], "rag_engine")
            self.assertEqual(lines[3]["fallback_used"], "keyword_retriever")
        finally:
            for l in loggers_to_attach:
                l.removeHandler(self.handler)


if __name__ == "__main__":
    unittest.main()
