#!/usr/bin/env python3
"""Consumer test for vcf-split 0.1.5-10.

Runs the installed vcf-split binary against the upstream Test/ fixture set
that ships inside the package and verifies every produced single-sample VCF
against the expected output checked in by upstream.
"""

import filecmp
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

COLUMNS = [str(column) for column in range(1, 12)]
ALL_FIELDS_PREFIX = "test-all-fields-"
LIMITED_FIELDS_PREFIX = "test-limited-fields-"


def run_split(exe, args, stdin_path, work_dir):
    with open(stdin_path, "rb") as stream:
        return subprocess.run(
            [str(exe)] + args,
            stdin=stream,
            cwd=str(work_dir),
            text=True,
            capture_output=True,
            check=True,
        )


def main(package_dir):
    if os.name == "nt":
        raise RuntimeError("vcf-split OHOS package targets POSIX platforms only")

    package = Path(package_dir)
    exe = package / "bin" / "vcf-split"
    fixture_dir = package / "share" / "vcf-split" / "Test"
    if not exe.is_file():
        raise FileNotFoundError(exe)
    if not fixture_dir.is_dir():
        raise FileNotFoundError(fixture_dir)

    assertions = 0

    version = subprocess.run([str(exe), "--version"], text=True, capture_output=True, check=True)
    version_text = version.stdout.strip()
    if "vcf-split 0.1.5-10" not in version_text:
        raise RuntimeError(f"unexpected version output: {version_text!r}")
    assertions += 1

    with tempfile.TemporaryDirectory(prefix="vcf-split-test-", dir=os.getcwd()) as tmp:
        work = Path(tmp)
        shutil.copy2(fixture_dir / "test.vcf", work / "test.vcf")
        for correct in sorted(fixture_dir.glob("correct-*.vcf")):
            shutil.copy2(correct, work / correct.name)

        run_split(exe, [ALL_FIELDS_PREFIX, "1", "11"], work / "test.vcf", work)
        run_split(
            exe,
            ["--fields", "chrom,pos,ref,alt,format", LIMITED_FIELDS_PREFIX, "1", "11"],
            work / "test.vcf",
            work,
        )

        for column in COLUMNS:
            for prefix in (ALL_FIELDS_PREFIX, LIMITED_FIELDS_PREFIX):
                produced = work / f"{prefix}{column}.vcf"
                expected = work / f"correct-{prefix.split('test-', 1)[1]}{column}.vcf"
                if not produced.is_file():
                    raise FileNotFoundError(produced)
                if not filecmp.cmp(produced, expected, shallow=False):
                    raise RuntimeError(f"fixture mismatch: {produced.name} != {expected.name}")
                assertions += 1

    print(f"vcf-split consumer test: {assertions} assertions passed ({version_text})")
    return assertions


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_vcf_split.py <package-folder>")
    main(sys.argv[1])
