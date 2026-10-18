#!/usr/bin/env python3
"""Complete consumer workflow for vcf-split 0.1.5-10.

Unlike test_vcf_split.py (which replays the upstream fixture diff), this script
drives the installed binary through realistic end-to-end VCF-splitting
workflows and asserts on the *semantics* of the produced single-sample files:
one sample column per output, record-level fidelity to the multi-sample input,
metadata preservation, and the documented command-line behaviours
(--max-calls early stop, --fields projection).
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

SAMPLE_COLUMN = "SAMPLE"
META_LINE_PREFIX = "##"
HEADER_PREFIX = "#CHROM"

ALL_FIELDS_PREFIX = "out-all-"
LIMITED_FIELDS_PREFIX = "out-limited-"
MAX_CALLS_PREFIX = "out-maxcalls-"


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


def read_vcf(path):
    """Return (meta_lines, header_columns, records)."""
    meta, header, records = [], [], []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if line.startswith(META_LINE_PREFIX):
                meta.append(line)
            elif line.startswith(HEADER_PREFIX):
                header = line.split("\t")
            elif line:
                records.append(line.split("\t"))
    return meta, header, records


def assert_single_sample_output(path, expected_record_count, counters):
    """Common invariant for every file vcf-split writes: one sample column."""
    meta, header, records = read_vcf(path)
    if not header:
        raise AssertionError(f"{path.name}: missing {HEADER_PREFIX} header line")
    if len(header) != 10:
        raise AssertionError(f"{path.name}: expected 10 columns, got {len(header)}")
    if header[-1] != SAMPLE_COLUMN:
        raise AssertionError(f"{path.name}: sample column is {header[-1]!r}, expected {SAMPLE_COLUMN!r}")
    if not meta:
        raise AssertionError(f"{path.name}: no ## metadata lines preserved")
    if len(records) != expected_record_count:
        raise AssertionError(
            f"{path.name}: expected {expected_record_count} records, got {len(records)}"
        )
    for record in records:
        if len(record) != len(header):
            raise AssertionError(f"{path.name}: record has {len(record)} fields, header has {len(header)}")
    counters["outputs"] += 1


def scenario_full_split(exe, fixture_dir, work_dir, counters):
    """Workflow 1: split an 11-sample VCF into 11 single-sample VCFs in one sweep."""
    input_vcf = work_dir / "multi-sample.vcf"
    with open(fixture_dir / "test.vcf", encoding="utf-8") as src, \
            open(input_vcf, "w", encoding="utf-8") as dst:
        dst.write(src.read())

    _, in_header, in_records = read_vcf(input_vcf)
    if len(in_header) != 20:
        raise AssertionError(f"fixture precondition: expected 20 input columns, got {len(in_header)}")
    counters["assertions"] += 1

    run_split(exe, [ALL_FIELDS_PREFIX, "1", "11"], input_vcf, work_dir)

    produced = sorted(work_dir.glob(f"{ALL_FIELDS_PREFIX}*.vcf"))
    if len(produced) != 11:
        raise AssertionError(f"workflow 1: expected 11 single-sample outputs, got {len(produced)}")
    counters["assertions"] += 1

    in_coords = [(r[0], r[1], r[3], r[4]) for r in in_records]
    for path in produced:
        assert_single_sample_output(path, len(in_records), counters)
        counters["assertions"] += 1
        _, _, out_records = read_vcf(path)
        out_coords = [(r[0], r[1], r[3], r[4]) for r in out_records]
        if out_coords != in_coords:
            raise AssertionError(f"{path.name}: CHROM/POS/REF/ALT diverged from the multi-sample input")
        counters["assertions"] += 1


def scenario_field_projection(exe, work_dir, counters):
    """Workflow 2: --fields drops the INFO column but keeps one sample."""
    input_vcf = work_dir / "multi-sample.vcf"
    run_split(
        exe,
        ["--fields", "chrom,pos,ref,alt,format", LIMITED_FIELDS_PREFIX, "1", "11"],
        input_vcf,
        work_dir,
    )

    produced = sorted(work_dir.glob(f"{LIMITED_FIELDS_PREFIX}*.vcf"))
    if len(produced) != 11:
        raise AssertionError(f"workflow 2: expected 11 outputs, got {len(produced)}")
    counters["assertions"] += 1

    for path in produced:
        _, _, records = read_vcf(path)
        for record in records:
            if record[7] != ".":
                raise AssertionError(f"{path.name}: INFO column not dropped by --fields: {record[7]!r}")
        counters["assertions"] += 1


def scenario_max_calls(exe, work_dir, counters):
    """Workflow 3: --max-calls stops the sweep after N variant calls."""
    input_vcf = work_dir / "multi-sample.vcf"
    run_split(exe, ["--max-calls", "3", MAX_CALLS_PREFIX, "1", "11"], input_vcf, work_dir)

    produced = sorted(work_dir.glob(f"{MAX_CALLS_PREFIX}*.vcf"))
    if len(produced) != 11:
        raise AssertionError(f"workflow 3: expected 11 outputs, got {len(produced)}")
    counters["assertions"] += 1

    for path in produced:
        assert_single_sample_output(path, 3, counters)
        counters["assertions"] += 1


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

    counters = {"assertions": 0, "outputs": 0}

    with tempfile.TemporaryDirectory(prefix="vcf-split-workflow-", dir=os.getcwd()) as tmp:
        work = Path(tmp)
        scenario_full_split(exe, fixture_dir, work, counters)
        scenario_field_projection(exe, work, counters)
        scenario_max_calls(exe, work, counters)

    print(
        f"vcf-split consumer workflows: 3 workflows, {counters['outputs']} single-sample VCFs produced, "
        f"{counters['assertions']} assertions passed"
    )
    return counters["assertions"]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_vcf_split_workflow.py <package-folder>")
    main(sys.argv[1])
