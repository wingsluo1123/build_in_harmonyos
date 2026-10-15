#!/usr/bin/env python3
"""Exercise the packaged sleepd/sleepctl binaries as a consumer would.

Usage: test_sleepd.py <bindir>

sleepd itself is a daemon needing real ACPI/sysfs power data and a
root-capable suspend command, so the consumer-level checks are:

1. ``sleepd -h`` exits 0 and prints its usage line — proves the binary
   is executable and its argument parser reached the usage branch.
2. ``sleepctl status`` prints the *documented default state*: the control
   file (/var/run/sleepd.ctl) and pid file (/var/run/sleepd.pid) do not
   exist on this device, and read_control() falls back to 0 (enabled)
   while getpid() fails, so the output is deterministic and asserted.
3. ``sleepctl`` with no argument rejects the call with a usage message on
   stderr and a non-zero exit status.

No root, no battery hardware and no writable /var/run are required.
"""
import os
import subprocess
import sys


def run(exe, args=()):
    proc = subprocess.run([exe] + list(args), capture_output=True, text=True,
                          timeout=60)
    return (proc.stdout or "") + (proc.stderr or ""), proc.returncode


def main():
    bindir = sys.argv[1]
    sleepd = os.path.join(bindir, "sleepd")
    sleepctl = os.path.join(bindir, "sleepctl")

    for exe in (sleepd, sleepctl):
        assert os.path.isfile(exe), exe
        assert os.access(exe, os.X_OK), "%s is not executable" % exe

    # 1) sleepd -h reaches the usage branch and exits 0.
    blob, rc = run(sleepd, ["-h"])
    assert rc == 0, "sleepd -h exited %d: %s" % (rc, blob)
    assert "Usage: sleepd" in blob, blob
    print("sleepd -h reached the usage branch")

    # 2) sleepctl status reports the documented default state (no control
    #    file, no pid file -> enabled / not-running).
    blob, rc = run(sleepctl, ["status"])
    assert "sleepd is not running" in blob, blob
    assert "sleeping enabled" in blob, blob
    print("sleepctl status reported the default state")

    # 3) sleepctl without arguments rejects the call.
    blob, rc = run(sleepctl)
    assert rc != 0, "sleepctl with no args must fail, got rc=%d" % rc
    assert "Usage: sleepctl" in blob, blob
    print("sleepctl rejected an argument-less call")

    print("SLEEPD-CONSUMER-OK")


main()
