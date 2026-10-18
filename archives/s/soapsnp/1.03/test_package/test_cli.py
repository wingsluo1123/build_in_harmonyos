"""Deterministic installed-CLI integration tests; no upstream test is replaced."""
from pathlib import Path
import json
import subprocess
import sys
import time

# Use fork/exec on OHOS for signed executables.
subprocess._USE_POSIX_SPAWN = False
BINARY = Path(sys.argv[1]).resolve()
FIXTURES = Path(__file__).resolve().parent / "fixtures"
OUT = Path.cwd() / "cli-test-results"
OUT.mkdir(exist_ok=True)
RESULTS = []
ASSERTIONS = 0
INVOCATIONS = 0


def check(value, message):
    global ASSERTIONS
    ASSERTIONS += 1
    if not value:
        raise AssertionError(message)


def run(name, args, expected=0, diagnostic=None):
    global INVOCATIONS
    output = OUT / (name + ".cns")
    inputs = {"-i": str(FIXTURES / "reference.soap"),
              "-d": str(FIXTURES / "reference.fa")}
    remaining = []
    iterator = iter(args)
    for arg in iterator:
        if arg in inputs:
            inputs[arg] = next(iterator)
        else:
            remaining.append(arg)
    cmd = [str(BINARY), "-i", inputs["-i"], "-d", inputs["-d"],
           "-o", str(output), "-L", "8", *remaining]
    INVOCATIONS += 1
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, timeout=90)
    (OUT / (name + ".stdout")).write_text(p.stdout)
    (OUT / (name + ".stderr")).write_text(p.stderr)
    (OUT / (name + ".command.json")).write_text(json.dumps(cmd))
    check(p.returncode == expected, f"{name}: exit {p.returncode}, {p.stderr}")
    if diagnostic is not None:
        check(diagnostic in p.stderr, f"{name}: diagnostic {p.stderr}")
        return []
    check("Consensus Done!" in p.stderr, f"{name}: completion marker missing")
    rows = [line.split() for line in output.read_text().splitlines()]
    check(bool(rows), f"{name}: no consensus rows")
    for row in rows:
        check(len(row) == 17, f"{name}: expected 17 fields: {row}")
    return rows


def reference_consensus():
    rows = run("reference", ["-I", str(FIXTURES / "fixed.mat")])
    check(len(rows) == 24, "reference: expected entire chromosome")
    for pos, row in enumerate(rows, 1):
        check(row[:3] == ["chr1", str(pos), "ACGT"[(pos - 1) % 4]],
              "reference: chromosome/coordinate/reference mismatch")
        if pos <= 16:
            check(row[3] == row[2], "reference: reference genotype mismatch")
            check(int(row[13]) == 20, "reference: depth mismatch")
        else:
            check(row[3] == row[2] and int(row[13]) == 0 and int(row[4]) == 1,
                  "reference: uncovered bases must have prior-reference call, depth 0, quality 1")


def variant_consensus():
    rows = run("variants", ["-i", str(FIXTURES / "variants.soap"),
                             "-I", str(FIXTURES / "fixed.mat")])
    check(rows[2][2:4] == ["G", "T"], "variants: expected G->T homozygous SNP")
    check(rows[4][2:4] == ["A", "R"], "variants: expected A/G heterozygous IUPAC R")
    check(int(rows[2][13]) == 20 and int(rows[4][13]) == 20,
          "variants: depth mismatch")
    check(sorted([int(rows[4][7]), int(rows[4][11])]) == [10, 10],
          "variants: expected two equally supported alleles")


def monoploid_consensus():
    rows = run("monoploid", ["-i", str(FIXTURES / "variants.soap"),
                              "-I", str(FIXTURES / "fixed.mat"), "-m"])
    check(rows[2][3] == "T", "monoploid: homozygous SNP changed")
    for row in rows:
        check(row[3] in "ACGTN", "monoploid: heterozygous call present")
    check(rows[4][3] in "AG", "monoploid: allele not supported by reads")


def snp_only():
    rows = run("snp-only", ["-i", str(FIXTURES / "variants.soap"),
                            "-I", str(FIXTURES / "fixed.mat"), "-q"])
    check([int(row[1]) for row in rows] == [3, 5], "snp-only: wrong SNP coordinates")
    check([row[3] for row in rows] == ["T", "R"], "snp-only: wrong genotype calls")


def calibration_roundtrip():
    matrix = OUT / "generated.mat"
    rows = run("calibrate", ["-M", str(matrix)])
    check(matrix.is_file(), "calibrate: matrix missing")
    lines = [line.split() for line in matrix.read_text().splitlines()]
    check(len(lines) == 41 * 8, "calibrate: wrong quality/cycle dimensions")
    check(all(len(line) == 18 for line in lines), "calibrate: wrong matrix width")
    reused = run("reuse-matrix", ["-I", str(matrix)])
    check(rows == reused, "calibrate: matrix reuse changed full consensus fields")
    check(all(row[3] == row[2] for row in rows[:16]),
          "calibrate: covered reference calls changed")


def missing_alignment():
    run("missing-alignment", ["-i", str(OUT / "absent.soap")], 1,
        "No such file or directory:")


def missing_reference():
    run("missing-reference", ["-d", str(OUT / "absent.fa")], 1,
        "No such file or directory:")


def unknown_chromosome():
    run("unknown-chromosome", ["-i", str(FIXTURES / "unknown.soap")], 255,
        "NOT found")


def missing_matrix():
    run("missing-matrix", ["-I", str(OUT / "absent.mat")], 1,
        "No such file or directory:")


CASES = [reference_consensus, variant_consensus, monoploid_consensus, snp_only,
         calibration_roundtrip, missing_alignment, missing_reference,
         unknown_chromosome, missing_matrix]
for case in CASES:
    began = time.monotonic()
    before = ASSERTIONS
    try:
        case()
    except Exception as exc:
        RESULTS.append({"case": case.__name__, "passed": False, "error": str(exc),
                        "assertions": ASSERTIONS - before})
        break
    RESULTS.append({"case": case.__name__, "passed": True,
                    "assertions": ASSERTIONS - before,
                    "seconds": round(time.monotonic() - began, 3)})
    print("PASS", case.__name__, "assertions", ASSERTIONS - before, flush=True)
record = {"cases_defined": len(CASES), "cases_run": len(RESULTS),
          "passed": sum(row["passed"] for row in RESULTS),
          "assertions_executed": ASSERTIONS, "cli_invocations": INVOCATIONS,
          "binary": str(BINARY), "results": RESULTS}
(OUT / "summary.json").write_text(json.dumps(record, indent=2))
print(json.dumps(record), flush=True)
sys.exit(0 if record["passed"] == len(CASES) else 1)
