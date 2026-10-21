"""检测器单测（标准库 unittest，无需第三方依赖）.

跑法：
    python3 -m unittest discover -s skills/runtime-service-absent-cleanup-guard/tests -v
"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))

import detect_absent_service_crash as det  # noqa: E402

UNGUARDED = """
static void
process_deactivate(Process* const proc)
{
  for (unsigned i = 0; i < proc->num_ports; ++i) {
    free(proc->ports[i]);
    lilv_instance_connect_port(proc->instance, i, NULL);
  }
}
"""

GUARDED = """
static void
process_deactivate(Process* const proc)
{
  for (unsigned i = 0; i < proc->num_ports; ++i) {
    free(proc->ports[i]);
    if (proc->instance) {
      lilv_instance_connect_port(proc->instance, i, NULL);
    }
  }
}
"""

NOT_A_CLEANUP_FUNC = """
static void
process_activate(Process* const proc)
{
  for (unsigned i = 0; i < proc->num_ports; ++i) {
    lilv_instance_connect_port(proc->instance, i, NULL);
  }
}
"""


class ScanSourceTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name, text):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def test_flags_unguarded_loop(self):
        self._write("process_setup.c", UNGUARDED)
        hits = det.scan_source(self.tmp)
        self.assertEqual(len(hits), 1)
        path, _lineno, detail = hits[0]
        self.assertTrue(path.endswith("process_setup.c"))
        self.assertIn("instance", detail)
        self.assertIn("without NULL guard", detail)

    def test_accepts_guarded_loop(self):
        self._write("process_setup.c", GUARDED)
        self.assertEqual(det.scan_source(self.tmp), [])

    def test_ignores_non_cleanup_functions(self):
        self._write("process_setup.c", NOT_A_CLEANUP_FUNC)
        self.assertEqual(det.scan_source(self.tmp), [])


class AnalyseLogTest(unittest.TestCase):
    def test_confirms_service_absent_plus_crash(self):
        log = "error: Failed to connect to audio system\nSegmentation fault\n"
        verdict, evidence = det.analyse_log(log)
        self.assertEqual(verdict, "yes")
        self.assertIn("service_absent", evidence)

    def test_rejects_crash_without_service_signature(self):
        verdict, _ = det.analyse_log("Segmentation fault (core dumped)\n")
        self.assertEqual(verdict, "no")

    def test_rejects_graceful_failure(self):
        verdict, _ = det.analyse_log(
            "error: Failed to connect to audio system\ngraceful exit\n")
        self.assertEqual(verdict, "no")

    def test_unknown_without_any_signature(self):
        verdict, _ = det.analyse_log("Plugin: some-uri\n")
        self.assertEqual(verdict, "unknown")


class CliTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name, text):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def _run(self, argv):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = det.main(argv)
        return rc, buf.getvalue()

    def test_scan_emits_sentinel(self):
        self._write("process_setup.c", UNGUARDED)
        rc, out = self._run(["scan", "--src", self.tmp])
        self.assertEqual(rc, 2)
        self.assertIn("ABSENT_SERVICE_CLEANUP_CANDIDATE=yes", out)
        self.assertIn("HIT=", out)

    def test_runtime_log_mode_confirmed(self):
        log = self._write("host.txt",
                          "Failed to connect to audio system\ncore dumped\n")
        rc, out = self._run(["runtime", "--log", log, "--rc", "139"])
        self.assertEqual(rc, 3)
        self.assertIn("ABSENT_SERVICE_CRASH_CONFIRMED=yes", out)

    def test_runtime_clean_log_is_ok(self):
        log = self._write("host.txt", "Plugin: x\nall good\n")
        rc, out = self._run(["runtime", "--log", log, "--rc", "0"])
        self.assertEqual(rc, 0)
        self.assertIn("ABSENT_SERVICE_CRASH_CONFIRMED=unknown", out)


if __name__ == "__main__":
    unittest.main()
