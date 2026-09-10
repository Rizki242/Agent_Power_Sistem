import os
import shutil
import tempfile
import unittest
from unittest import mock

from typer.testing import CliRunner

from pple.cli.main import app
from src import domain_measurements as dm

runner = CliRunner()


class DomainCliTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="pple_domain_cli_")
        self._env = mock.patch.dict(os.environ, {"MCSA_DATA_DIR": self.root})
        self._env.start()

    def tearDown(self):
        self._env.stop()
        shutil.rmtree(self.root, ignore_errors=True)

    def _write_csv(self, name: str, content: str) -> str:
        path = os.path.join(self.root, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path


class DomainListTests(DomainCliTestCase):
    def test_lists_all_five_domains(self):
        result = runner.invoke(app, ["domain", "list"])
        self.assertEqual(result.exit_code, 0)
        for domain in dm.DOMAINS:
            self.assertIn(domain, result.stdout)


class DomainUploadTests(DomainCliTestCase):
    def test_upload_writes_rows_into_the_canonical_store(self):
        path = self._write_csv("uji.csv", "equipment,test_date,h2\nTRF-1,2026-05-01,20\n")
        result = runner.invoke(app, ["domain", "upload", "DGA", path])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Tersimpan 1 pengukuran", result.stdout)
        self.assertEqual(len(dm.load_measurements("DGA")), 1)

    def test_preview_only_writes_nothing(self):
        path = self._write_csv("uji.csv", "equipment,test_date,h2\nTRF-1,2026-05-01,20\n")
        result = runner.invoke(app, ["domain", "upload", "DGA", path, "--preview-only"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("--preview-only", result.stdout)
        self.assertTrue(dm.load_measurements("DGA").empty)

    def test_unknown_domain_exits_nonzero(self):
        path = self._write_csv("uji.csv", "equipment,test_date,h2\nTRF-1,2026-05-01,20\n")
        result = runner.invoke(app, ["domain", "upload", "tidak-ada", path])
        self.assertNotEqual(result.exit_code, 0)

    def test_missing_file_exits_nonzero(self):
        result = runner.invoke(app, ["domain", "upload", "DGA", os.path.join(self.root, "tidak-ada.csv")])
        self.assertNotEqual(result.exit_code, 0)


class DomainMeasurementsTests(DomainCliTestCase):
    def test_shows_stored_rows(self):
        dm.append_measurements("DGA", [
            {"equipment": "TRF-1", "test_date": "2026-05-01", "parameter": "h2", "value": 20},
        ])
        result = runner.invoke(app, ["domain", "measurements", "DGA"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("TRF-1", result.stdout)
        self.assertIn("h2", result.stdout)


class DomainReportTests(DomainCliTestCase):
    def test_builds_a_csv_report_file(self):
        dm.append_measurements("TRIBOLOGY", [
            {"equipment": "GBX-1", "test_date": "2026-05-01", "parameter": "viscosity_40c", "value": 46.0},
        ])
        out = os.path.join(self.root, "laporan.csv")
        result = runner.invoke(app, ["domain", "report", "TRIBOLOGY", out])
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(os.path.exists(out))
        self.assertGreater(os.path.getsize(out), 0)


class DomainVibrasiReportTests(DomainCliTestCase):
    def test_builds_the_detail_report_docx(self):
        dm.append_measurements("VIBRASI", [
            {"equipment": "Motor ID Fan 1#1", "test_date": "2024-09-09", "parameter": "pt1_v", "value": 0.26},
        ])
        out = os.path.join(self.root, "detail.docx")
        result = runner.invoke(app, ["domain", "vibrasi-report", "Motor ID Fan 1#1", out])
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(os.path.exists(out))
        self.assertGreater(os.path.getsize(out), 100)

    def test_unknown_equipment_exits_nonzero(self):
        out = os.path.join(self.root, "detail.docx")
        result = runner.invoke(app, ["domain", "vibrasi-report", "Tidak Ada", out])
        self.assertNotEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
