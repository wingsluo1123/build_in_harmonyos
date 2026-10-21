#!/usr/bin/env python3
"""CLI-level consumer assertions for the packaged xwiishow binary.

Invoked from test_package/conanfile.py with the conanrun environment so the
runtime shared libraries (libxwiimote.so.2 from the package, libudev.so.1 from
the eudev dependency) are locatable. Every assertion executes the shipped
binary and inspects its real stdout/stderr and exit status.

`xwiishow list` is the one code path of the tool that is fully headless: it
constructs an xwii_monitor (libudev enumeration) and prints the device list
without ever calling initscr(), so it runs on a machine with no X server, no
TTY and no attached Wii Remote.
"""

import subprocess
import sys


def run(binary, *args, timeout=30):
    return subprocess.run(
        [binary, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def main():
    binary = sys.argv[1]
    checks = 0
    failures = 0

    def check(cond, message, extra=""):
        nonlocal checks, failures
        checks += 1
        if cond:
            print(f"PASS: {message}")
        else:
            failures += 1
            print(f"FAIL: {message}{(' — ' + extra) if extra else ''}")

    # 1-3. `xwiishow list`: udev enumeration path, no ncurses initialisation.
    result = run(binary, "list")
    print(f"INFO: xwiishow list exited {result.returncode}")
    print(f"INFO: stdout:\n{result.stdout}")
    if result.stderr:
        print(f"INFO: stderr:\n{result.stderr}")
    check(result.returncode == 0,
          "xwiishow list exits 0",
          f"rc={result.returncode}")
    check("Listing connected Wii Remote devices:" in result.stdout,
          "xwiishow list prints the enumeration header")
    check("End of device list" in result.stdout,
          "xwiishow list reaches the end of the device list")

    # 4-5. `xwiishow -h`: exit code + usage text. Upstream *does* handle `-h`:
    # main() has `if (argc < 2 || !strcmp(argv[1], "-h"))` -> prints "Usage:"
    # and returns abs(-1) == 1. Only `--help`/`--version` are unhandled and
    # fall through to the device-open branch. The exit code is asserted too.
    result = run(binary, "-h")
    print(f"INFO: xwiishow -h exited {result.returncode}")
    check(result.returncode == 1,
          "xwiishow -h exits 1 (upstream abs(-1) by design)",
          f"rc={result.returncode}")
    check("Usage:" in result.stdout and "xwiishow list" in result.stdout,
          "xwiishow -h prints the upstream usage text")

    print(f"xwiishow CLI consumer checks: {checks} run, {failures} failed")
    print("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,"
          "\"suite\":\"test_xwiishow_cli.py\","
          f"\"discovered\":{checks},\"passedCount\":{checks - failures}}}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
