"""Run every upstream TAP script with a terminal on stdin.

mblaze uses isatty(0) to distinguish its default message sequence from stdin.
The upstream `prove` command loses this property in noninteractive CI jobs, so
run the same scripts directly and check their TAP plans and assertions.
"""

import os
import pty
import re
import subprocess
import sys
from pathlib import Path


def parse_tap(output: str, returncode: int) -> tuple[int, int, bool]:
    """Count executed assertions; reject skips, TODOs and incomplete plans."""
    plans = re.findall(r"^1\.\.(\d+)\s*$", output, re.MULTILINE)
    ok_lines = re.findall(r"^ok(?:\s[^\n]*)?$", output, re.MULTILINE)
    passed = sum(
        not re.search(r"#\s*(?:SKIP|TODO)\b", line, re.IGNORECASE)
        for line in ok_lines
    )
    failed = len(re.findall(r"^not ok(?:\s|$)", output, re.MULTILINE))
    expected = int(plans[0]) if len(plans) == 1 else -1
    valid = returncode == 0 and expected >= 0 and passed == expected and failed == 0
    return expected, passed, valid


def run_test(test: Path, source: Path, shell: str) -> tuple[int, int, bool]:
    master, slave = pty.openpty()
    try:
        env = os.environ.copy()
        env["PATH"] = f"{source}{os.pathsep}{env.get('PATH', '')}"
        process = subprocess.run(
            [shell, "-e", str(test)],
            cwd=source,
            env=env,
            stdin=slave,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    finally:
        os.close(slave)
        os.close(master)

    output = process.stdout.decode("utf-8", errors="replace")
    print(f"== {test.name} ==\n{output}", end="" if output.endswith("\n") else "\n")
    expected, passed, valid = parse_tap(output, process.returncode)
    if not valid:
        print(
            f"FAIL {test.name}: return={process.returncode}, "
            f"plan={expected}, passed={passed}, output={output!r}",
            file=sys.stderr,
        )
    return expected, passed, valid


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_upstream_tests.py SOURCE_DIR", file=sys.stderr)
        return 2
    source = Path(sys.argv[1]).resolve()
    shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
    tests = sorted((source / "t").glob("[0-9]*.t"))
    if len(tests) != 12:
        print(f"expected 12 upstream TAP files, found {len(tests)}", file=sys.stderr)
        return 1
    total = 0
    for test in tests:
        expected, _passed, valid = run_test(test, source, shell)
        if not valid:
            return 1
        total += expected
    if total != 135:
        print(f"expected 135 upstream assertions, found {total}", file=sys.stderr)
        return 1
    print(f"UPSTREAM PASS: {len(tests)} files, {total} assertions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
