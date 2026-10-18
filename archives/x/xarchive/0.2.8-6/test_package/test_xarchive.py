#!/usr/bin/env python3
"""Deterministic consumer smoke checks for the packaged xarchive binary.

xarchive 0.2.8-6 is a GTK+2 GUI application with no upstream test suite.
Running it with no arguments reaches gtk_init() and fails headless with
"cannot open display".  Running `xarchive --help` instead exits with code 0
inside g_option_context_parse() (gtk_get_option_group's help handling) —
before gtk_init() — so on a headless target it still proves the binary
loads its full dynamic-linking chain (libc/gtk-x11/gdk/glib/...) and
parses command-line options.  Full GUI verification needs an X server
(R40 human-confirmation boundary).
"""

import subprocess
import sys

checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


def main():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <path-to-xarchive>", file=sys.stderr)
        return 2

    xarchive_bin = sys.argv[1]
    check(len(xarchive_bin) > 0, "xarchive binary path argument is empty")

    completed = subprocess.run(
        [xarchive_bin, "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    output = (completed.stdout or "") + (completed.stderr or "")
    check(completed.returncode == 0, f"xarchive --help exit code: {completed.returncode}, output: {output!r}")
    check("Usage" in output or "用法" in output, f"--help output has no usage section: {output!r}")
    check("xarchive" in output.lower(), f"--help output does not identify the binary: {output!r}")
    check("0.2.8-6" not in output, "version banner leaked into --help output")

    print(f"xarchive consumer smoke: {checks}/{checks} checks passed")
    print("R40 note: full GUI behaviour (window, drag-drop archive ops, wrapper "
          "invocations of tar/zip/rar/7z/deb) requires an X server and is outside "
          "headless CI coverage — needs human confirmation on a real device.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
