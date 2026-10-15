#!/usr/bin/env python3
"""Mirror of upstream pylorcon2/test.py unittest suite for HMBS evidence.

Upstream source: https://github.com/kismetwireless/lorcon pylorcon2/test.py
(tag 2020.06.06, also present on master). It defines exactly 10 unittest
methods in class PyLorcon2TestCase:

  testGetVersion, testListDrivers, testFindDriver, testAutoDriver,
  testInjection, testTimeout, testVap, testGetDriverName, testChannel, testMAC

Upstream setUp does ``self.ctx = PyLorcon2.Context('wlan0')`` for every
test, but testGetVersion / testListDrivers / testFindDriver never touch
self.ctx (verified against the tag source fetched 2026-10-15):
testGetVersion only calls ``PyLorcon2.get_version()`` and asserts
``type(version) == int``. Hence testGetVersion is hardware-independent and
is executed here for real (executed>0 for rule4); the other 9 require a
monitor-mode 802.11 interface plus an injection-capable driver and are
reported as explicit unittest skips (ohos_feature).

testGetVersion execution route (no hardware, no Python binding): the
test_package consumer binary ``lorcon_test`` already calls the identical
C API ``lorcon_get_version()`` and prints ``CHECK-OK: version=<N>``.
This test runs that binary via subprocess, parses the version line with a
single deterministic regex (no word-count arithmetic), and asserts
``type(version) is int and version != 0`` -- the exact upstream
assertion mapped onto the packaged C library. Binary path arrives via
``LORCON_TEST_BIN`` (set by test_package/conanfile.py, which has just
built it); fallback search covers manual runs. Missing binary or
unparsable output is a FAILURE (not a skip):宁缺毋假.

The remaining demo scripts (pylorcon2/test-multi.py, test-packet.py,
test-packet-filter.py, test-packet-scapy.py, ruby-lorcon/test.rb) are
hardware/pcap demos with zero assertions, not an automated suite.
Makefile.in defines no check/test target (verified from raw Makefile.in:
only all/install/clean/distclean/dep/depend targets).

Discovered count comes from parsing this file for ``^    def test``
(python_def method); executed/passed/skipped come from parsing
``python3 -m unittest -v`` per-test lines (``... ok|skipped|FAIL|ERROR``),
one line per test, no word-count arithmetic. See
test_package/conanfile.py _emit_upstream_marker.
"""

import os
import re
import subprocess
import unittest


UPSTREAM_ORIGIN = "pylorcon2/test.py (kismetwireless/lorcon tag 2020.06.06)"
UPSTREAM_IFACE = "wlan0"
SKIP_REASON = (
    "requires monitor-mode 802.11 interface 'wlan0' + injection-capable "
    "driver (upstream setUp Context('wlan0'), open_injmon/open_monitor/"
    "send_bytes/set_channel/set_hwmac/auto_driver); HarmonyOS PC provides "
    "no wireless injection path (ohos_feature)"
)


def _probe_wireless():
    """Emit deterministic hardware-absence evidence to stdout."""
    lines = []
    net_dir = "/sys/class/net"
    try:
        entries = sorted(os.listdir(net_dir))
    except OSError as exc:
        lines.append("UPSTREAM-PROBE: /sys/class/net unreadable: %s" % exc)
        entries = []
    else:
        lines.append("UPSTREAM-PROBE: /sys/class/net entries=%s" % entries)
    wireless = []
    for entry in entries:
        wireless_path = os.path.join(net_dir, entry, "wireless")
        if os.path.exists(wireless_path):
            wireless.append(entry)
    lines.append("UPSTREAM-PROBE: wireless interfaces=%s" % wireless)
    lines.append("UPSTREAM-PROBE: upstream iface '%s' present=%s"
                 % (UPSTREAM_IFACE, UPSTREAM_IFACE in entries))
    lines.append("UPSTREAM-PROBE: origin=%s" % UPSTREAM_ORIGIN)
    for line in lines:
        print(line, flush=True)
    return lines


_PROBE_LINES = _probe_wireless()


def _find_lorcon_test_binary():
    """Locate the packaged consumer binary that calls lorcon_get_version."""
    env_path = os.environ.get("LORCON_TEST_BIN", "")
    if env_path and os.path.isfile(env_path):
        return env_path
    # Manual-run fallbacks: direct-file checks only (no recursive walk;
    # the preflight always sets LORCON_TEST_BIN, and a full tree walk on
    # a large workspace hangs local runs). Check cwd / module dir and up
    # to two parents for a directly nested lorcon_test / lorcon_test.exe.
    try:
        here = os.path.abspath(os.getcwd())
    except OSError:
        here = ""
    probe_dirs = []
    if here:
        probe_dirs.append(here)
        parent = os.path.dirname(here)
        if parent and parent not in probe_dirs:
            probe_dirs.append(parent)
        grand = os.path.dirname(parent) if parent else ""
        if grand and grand not in probe_dirs:
            probe_dirs.append(grand)
    try:
        module_dir = os.path.dirname(os.path.abspath(__file__))
    except Exception:
        module_dir = ""
    if module_dir and module_dir not in probe_dirs:
        probe_dirs.append(module_dir)
    for directory in probe_dirs:
        if not directory or not os.path.isdir(directory):
            continue
        for name in ("lorcon_test", "lorcon_test.exe"):
            direct = os.path.join(directory, name)
            try:
                if os.path.isfile(direct):
                    return direct
            except OSError:
                continue
    # Last resort: PATH lookup (conanrun env provides it).
    try:
        import shutil as _shutil
        found = _shutil.which("lorcon_test")
        if found:
            return found
    except Exception:
        pass
    return ""


class PyLorcon2UpstreamAudit(unittest.TestCase):
    """Identical 10 test IDs to upstream PyLorcon2TestCase.

    testGetVersion executes for real (hardware-independent upstream
    assertion); the other 9 skip with ohos_feature evidence.
    """

    def testGetVersion(self):
        # Upstream: version = PyLorcon2.get_version();
        # self.assertEqual(type(version), int). Uses no Context/iface.
        bin_path = _find_lorcon_test_binary()
        self.assertTrue(
            bin_path,
            "lorcon_test binary not found (LORCON_TEST_BIN=%r); "
            "cannot execute upstream testGetVersion without the "
            "packaged library" % os.environ.get("LORCON_TEST_BIN", ""))
        proc = subprocess.run(
            [bin_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
        )
        output = proc.stdout or ""
        self.assertEqual(
            proc.returncode, 0,
            "lorcon_test exit=%s, output tail=%r"
            % (proc.returncode, output[-500:]))
        match = re.search(r"CHECK-OK: version=(\d+)", output)
        self.assertIsNotNone(
            match,
            "lorcon_test output lacks CHECK-OK version line; tail=%r"
            % output[-500:])
        version = int(match.group(1))
        # Exact upstream assertion: type must be int (and non-zero, as the
        # consumer test already pins down). No stdout print here: unittest
        # -v keeps "... ok" on the same line only when the test is silent;
        # any print splits the verdict onto its own line and breaks the
        # deterministic per-test line parse in conanfile.py (no arithmetic
        # fallback allowed). Evidence for this executed test is the "... ok"
        # line itself plus the consumer binary CHECK-OK line parsed above.
        self.assertEqual(type(version), int)
        self.assertTrue(version != 0, "lorcon_get_version returned 0")

    def testListDrivers(self):
        self.skipTest(SKIP_REASON)

    def testFindDriver(self):
        self.skipTest(SKIP_REASON)

    def testAutoDriver(self):
        self.skipTest(SKIP_REASON)

    def testInjection(self):
        self.skipTest(SKIP_REASON)

    def testTimeout(self):
        self.skipTest(SKIP_REASON)

    def testVap(self):
        self.skipTest(SKIP_REASON)

    def testGetDriverName(self):
        self.skipTest(SKIP_REASON)

    def testChannel(self):
        self.skipTest(SKIP_REASON)

    def testMAC(self):
        self.skipTest(SKIP_REASON)


if __name__ == "__main__":
    unittest.main(verbosity=2)
