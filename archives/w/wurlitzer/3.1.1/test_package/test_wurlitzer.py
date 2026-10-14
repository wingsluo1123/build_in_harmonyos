import io
import os
import sys
import unittest

import wurlitzer


MODULE_DIR = os.path.realpath(sys.argv.pop(1))


class ConsumerTests(unittest.TestCase):
    def test_installed_module(self):
        self.assertEqual(os.path.dirname(os.path.realpath(wurlitzer.__file__)), MODULE_DIR)
        self.assertEqual(wurlitzer.__version__, "3.1.1")

    def test_native_unicode_capture(self):
        with wurlitzer.pipes() as (stdout, stderr):
            wurlitzer.libc.printf("HarmonyOS 中文\n".encode("utf8"))
            wurlitzer.libc.fprintf(wurlitzer.c_stderr_p, b"native error\n")
        self.assertEqual(stdout.read(), "HarmonyOS 中文\n")
        self.assertEqual(stderr.read(), "native error\n")

    def test_native_bytes(self):
        with wurlitzer.pipes(encoding=None) as (stdout, stderr):
            wurlitzer.libc.printf(b"native bytes\n")
        self.assertEqual(stdout.read(), b"native bytes\n")
        self.assertEqual(stderr.read(), b"")

    def test_forward_and_restore(self):
        output = io.StringIO()
        capture = wurlitzer.Wurlitzer(stdout=output, stderr=wurlitzer.STDOUT)
        with capture:
            wurlitzer.libc.printf(b"forwarded\n")
        self.assertEqual(output.getvalue(), "forwarded\n")
        self.assertFalse(capture.thread.is_alive())


if __name__ == "__main__":
    unittest.main(verbosity=2)
