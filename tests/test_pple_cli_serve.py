import unittest
from unittest import mock

from typer.testing import CliRunner

from pple.cli.main import app

runner = CliRunner()


class ServeApiTests(unittest.TestCase):
    def test_serve_api_prints_banner_and_calls_run_server_main(self):
        with mock.patch("run_server.main") as mocked_main:
            result = runner.invoke(app, ["serve", "api", "--port", "9001"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("PPLE READY", result.stdout)
        self.assertIn("localhost:9001", result.stdout)
        self.assertIn("Swagger", result.stdout)
        mocked_main.assert_called_once_with(host="0.0.0.0", port=9001)

    def test_serve_api_defaults_when_no_flags_given(self):
        with mock.patch("run_server.main") as mocked_main, \
             mock.patch.dict("os.environ", {}, clear=False):
            result = runner.invoke(app, ["serve", "api"])
        self.assertEqual(result.exit_code, 0)
        mocked_main.assert_called_once_with(host="0.0.0.0", port=8000)

    def test_serve_api_respects_host_env_var(self):
        with mock.patch("run_server.main") as mocked_main, \
             mock.patch.dict("os.environ", {"HOST": "127.0.0.1", "PORT": "8123"}):
            result = runner.invoke(app, ["serve", "api"])
        self.assertEqual(result.exit_code, 0)
        mocked_main.assert_called_once_with(host="127.0.0.1", port=8123)


class ServeFrontendTests(unittest.TestCase):
    def test_serve_frontend_runs_npm_dev(self):
        with mock.patch("subprocess.run") as mocked_run:
            result = runner.invoke(app, ["serve", "frontend"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("localhost:5173", result.stdout)
        mocked_run.assert_called_once_with(["npm", "--prefix", "frontend", "run", "dev"])


class ServeAllTests(unittest.TestCase):
    def test_serve_all_starts_api_subprocess_and_blocks_on_frontend(self):
        with mock.patch("subprocess.Popen") as mocked_popen, \
             mock.patch("subprocess.run") as mocked_run:
            result = runner.invoke(app, ["serve", "all", "--port", "9002"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("PPLE READY", result.stdout)
        self.assertIn("localhost:9002", result.stdout)
        self.assertIn("localhost:5173", result.stdout)

        popen_args = mocked_popen.call_args[0][0]
        self.assertIn("uvicorn", popen_args)
        self.assertIn("--port", popen_args)
        self.assertIn("9002", popen_args)
        self.assertIn("--reload", popen_args)

        mocked_run.assert_called_once_with(["npm", "--prefix", "frontend", "run", "dev"])
        mocked_popen.return_value.terminate.assert_called_once()

    def test_serve_all_terminates_api_even_if_frontend_raises(self):
        with mock.patch("subprocess.Popen") as mocked_popen, \
             mock.patch("subprocess.run", side_effect=RuntimeError("npm exploded")):
            with self.assertRaises(RuntimeError):
                runner.invoke(app, ["serve", "all"], catch_exceptions=False)
        mocked_popen.return_value.terminate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
