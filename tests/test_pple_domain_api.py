import os
import shutil
import tempfile
import unittest
from unittest import mock
from urllib.parse import quote

from fastapi.testclient import TestClient

from api_server import app
from src import domain_measurements as dm


class DomainApiTestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.root = tempfile.mkdtemp(prefix="pple_domain_api_")
        self._env = mock.patch.dict(os.environ, {"MCSA_DATA_DIR": self.root})
        self._env.start()

    def tearDown(self):
        self._env.stop()
        shutil.rmtree(self.root, ignore_errors=True)


class ListDomainsTests(DomainApiTestCase):
    def test_lists_all_five_domains_with_their_parameters(self):
        response = self.client.get("/api/v2/domain/domains")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        domains = {row["domain"] for row in body["domains"]}
        self.assertEqual(domains, set(dm.DOMAINS))
        vibrasi = next(row for row in body["domains"] if row["domain"] == "VIBRASI")
        self.assertIn("overall_rms", {p["key"] for p in vibrasi["parameters"]})


class UnknownDomainTests(DomainApiTestCase):
    def test_unknown_domain_is_a_404_not_a_500(self):
        response = self.client.get("/api/v2/domain/tidak-ada/measurements")
        self.assertEqual(response.status_code, 404)


class TemplateAndUploadTests(DomainApiTestCase):
    def test_template_download_has_identity_and_parameter_columns(self):
        response = self.client.get("/api/v2/domain/DGA/template.csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("equipment", response.text)
        self.assertIn("h2", response.text)

    def test_preview_reports_valid_rows_without_writing_anything(self):
        csv_bytes = b"equipment,test_date,h2\nTRF-1,2026-05-01,20\n"
        response = self.client.post(
            "/api/v2/domain/DGA/preview",
            files={"file": ("uji.csv", csv_bytes, "text/csv")},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["valid_count"], 1)
        self.assertTrue(dm.load_measurements("DGA").empty)

    def test_commit_writes_rows_into_the_canonical_store(self):
        csv_bytes = b"equipment,test_date,h2\nTRF-1,2026-05-01,20\n"
        response = self.client.post(
            "/api/v2/domain/DGA/commit",
            files={"file": ("uji.csv", csv_bytes, "text/csv")},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["written"], 1)
        self.assertEqual(len(dm.load_measurements("DGA")), 1)

    def test_a_duplicate_aliased_column_is_reported_on_commit_too(self):
        csv_bytes = b"equipment,test_date,h2,hidrogen\nTRF-1,2026-05-01,20,25\n"
        response = self.client.post(
            "/api/v2/domain/DGA/commit",
            files={"file": ("uji.csv", csv_bytes, "text/csv")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("hidrogen", response.json()["duplicate_columns"])


class MeasurementsAndSummaryTests(DomainApiTestCase):
    def setUp(self):
        super().setUp()
        dm.append_measurements("DGA", [
            {"equipment": "TRF-1", "test_date": "2026-05-01", "parameter": "h2", "value": 20},
            {"equipment": "TRF-1", "test_date": "2026-05-01", "parameter": "co2", "value": 500},
        ])

    def test_measurements_endpoint_returns_stored_rows(self):
        response = self.client.get("/api/v2/domain/DGA/measurements", params={"equipment": "TRF-1"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 2)
        self.assertEqual({row["parameter"] for row in body["measurements"]}, {"h2", "co2"})

    def test_bad_date_format_is_a_422_not_a_500(self):
        response = self.client.get("/api/v2/domain/DGA/measurements", params={"start": "01-05-2026"})
        self.assertEqual(response.status_code, 422)

    def test_summary_returns_a_verdict_for_the_equipment(self):
        response = self.client.get("/api/v2/domain/DGA/summary")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["reading_count"], 2)
        self.assertEqual([v["equipment"] for v in body["verdicts"]], ["TRF-1"])


class ReportDownloadTests(DomainApiTestCase):
    def setUp(self):
        super().setUp()
        dm.append_measurements("TRIBOLOGY", [
            {"equipment": "GBX-1", "test_date": "2026-05-01", "parameter": "viscosity_40c", "value": 46.0},
        ])

    def test_csv_report_download(self):
        response = self.client.get("/api/v2/domain/TRIBOLOGY/report", params={"format": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["content-type"])
        self.assertIn("GBX-1", response.text)

    def test_docx_report_download(self):
        response = self.client.get("/api/v2/domain/TRIBOLOGY/report", params={"format": "docx"})
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 100)

    def test_unsupported_format_is_a_422(self):
        response = self.client.get("/api/v2/domain/TRIBOLOGY/report", params={"format": "xlsx"})
        self.assertEqual(response.status_code, 422)


class VibrasiDetailReportTests(DomainApiTestCase):
    def test_returns_a_word_document_for_equipment_with_readings(self):
        dm.append_measurements("VIBRASI", [
            {"equipment": "Motor ID Fan 1#1", "test_date": "2024-09-09", "parameter": "pt1_v", "value": 0.26},
        ])
        response = self.client.get(f"/api/v2/domain/vibrasi/report/{quote('Motor ID Fan 1#1', safe='')}")
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 100)

    def test_404_for_equipment_with_no_readings(self):
        response = self.client.get("/api/v2/domain/vibrasi/report/Tidak Ada")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
