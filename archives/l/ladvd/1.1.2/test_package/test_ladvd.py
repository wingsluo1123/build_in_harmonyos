#!/usr/bin/env python3
import os
import struct
import subprocess
import sys


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def run_help(path, expected_name):
    result = subprocess.run(
        [path, "-h"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    check(result.returncode == 1, f"{expected_name} -h returned {result.returncode}")
    check("ladvd version 1.1.2" in result.stderr, f"missing version: {result.stderr}")
    check(f"Usage: {expected_name}" in result.stderr, f"missing usage: {result.stderr}")


def run_harmony_daemon_once(path):
    """Run one complete installed-daemon lifecycle on the native target."""
    result = subprocess.run(
        [path, "-d", "-o", "-s", "-L"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=15,
    )
    check(result.returncode == 0, f"one-shot daemon returned {result.returncode}")
    check(len(result.stdout) == 24, "one-shot daemon did not emit a pcap header")
    magic, major, minor, _, _, snaplen, network = struct.unpack(
        "=IHHIIII", result.stdout
    )
    check(
        (magic, major, minor, snaplen, network)
        == (0xA1B2C3D4, 2, 4, 1518, 1),
        "one-shot daemon emitted an invalid Ethernet pcap header",
    )
    diagnostics = result.stderr.decode("utf-8", errors="replace")
    check("ladvd 1.1.2 running" in diagnostics, "daemon did not reach its event flow")
    check("child exited with return code 0" in diagnostics, "child did not exit cleanly")
    print("HarmonyOS consumer case: installed one-shot daemon lifecycle passed")


def main():
    check(len(sys.argv) == 2, "expected the tested package bin directory")
    bin_dir = os.path.realpath(sys.argv[1])
    ladvd = os.path.join(bin_dir, "ladvd")
    ladvdc = os.path.join(bin_dir, "ladvdc")
    check(os.path.isfile(ladvd), "ladvd is not a packaged regular file")
    check(os.path.lexists(ladvdc), "ladvdc package entry is missing")
    run_help(ladvd, "ladvd")
    run_help(ladvdc, "ladvdc")
    run_harmony_daemon_once(ladvd)
    print("ladvd package commands: 1 end-to-end case and 13 assertions passed")


if __name__ == "__main__":
    main()
