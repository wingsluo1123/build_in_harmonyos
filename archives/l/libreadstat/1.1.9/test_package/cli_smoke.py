#!/usr/bin/env python3
"""CLI check for libreadstat/1.1.9 on HarmonyOS PC.

Driven by test_package/conanfile.py::test().  Runs the *packaged* `readstat`
executable over the .sav fixture that consumer_round_trip produced and asserts
on its output, so this is a real verification rather than a "did it exit 0"
smoke call.

Usage: cli_smoke.py <readstat-binary> <fixture.sav>
Exit:  0 = all assertions passed, 1 = at least one failed.
"""
import subprocess
import sys

failures = 0


def check(condition, what):
    global failures
    if condition:
        print(f"ok   : {what}")
    else:
        print(f"FAIL : {what}")
        failures += 1


def run(argv):
    proc = subprocess.run(argv, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def main():
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <readstat-binary> <fixture.sav>")
        return 2
    cli, fixture = sys.argv[1], sys.argv[2]

    rc, out, err = run([cli, fixture])
    check(rc == 0, f"`readstat <fixture>` exits 0 (rc={rc})")
    check("SPSS binary file (SAV)" in out, "metadata listing reports the SAV format")
    check("Columns: 3" in out, "metadata listing reports 3 columns")
    check("Rows: 3" in out, "metadata listing reports 3 rows")
    check("Table label: readstat ohos consumer" in out,
          "metadata listing reports the file label written by the fixture")
    if rc != 0:
        print(err.strip()[:2000])

    rc, out, err = run([cli, fixture, "-"])
    check(rc == 0, f"`readstat <fixture> -` (CSV to stdout) exits 0 (rc={rc})")
    if rc != 0:
        print(err.strip()[:2000])
        print(f"readstat 1.1.9 packaged CLI check: FAIL ({failures} failure(s))")
        return 1

    lines = [line for line in out.splitlines() if line.strip()]
    check(len(lines) == 4, f"CSV output has header + 3 data rows (got {len(lines)} line(s))")
    check(lines[0] == '"age","grp","name"' if lines else False,
          'CSV header is "age","grp","name"')
    check(len(lines) > 1 and lines[1].startswith("42.500000,7.000000,"),
          "first data row carries the values written by the fixture")
    check(len(lines) > 3 and '"gamma"' in lines[3], "last data row carries the string value")

    print(f"readstat 1.1.9 packaged CLI check: {'PASS' if failures == 0 else 'FAIL'} "
          f"({failures} failure(s))")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
