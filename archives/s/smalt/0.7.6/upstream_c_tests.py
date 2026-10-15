#!/usr/bin/env python3
"""Drive smalt 0.7.6's two distributed C test programs and assert their output.

Upstream ships two C test programs in the release tarball:

  test/sequenceReverseComplement_test.c   in check_PROGRAMS, so `make check`
                                          builds it - but automake only runs
                                          what TESTS lists, and TESTS holds the
                                          six Python drivers, so it never runs.
  test/diffstr_test.c                     in EXTRA_PROGRAMS, built on request.

Neither program contains an assertion: both are usage-driven harnesses that
print a result and exit 0 (sequenceReverseComplement_test) or exit with the
internal error code (diffstr_test).  This script supplies the missing
judgement: it feeds each harness real input and compares the output against
the behaviour measured on the unmodified upstream sources, so the two programs
become pass/fail test cases instead of "it did not crash".

Checks (independent, each separately judged - this is the counting unit used
in test_package/MANIFEST.yml and in the PR test tables):

  C1  sequenceReverseComplement_test over a 2-record FASTA file: rc 0, the
      count line "Revese complement of 2 sequences." (upstream's own spelling),
      and both output sequences equal the reverse complement of the input.
  C2  the same harness over a 2-read FASTQ file: sequences reverse
      complemented *and* quality strings reversed (a separate code path from
      C1 - seqFastqReverse() has to flip the quality vector too), headers and
      the '+' separator preserved.
  C3  error path: an empty input file must be rejected (rc != 0) with
      "wrong FASTQ/FASTA format".
  C4  error path: a missing input file must be rejected (rc != 0) with
      "could not open file".
  C5  diffstr_test over the CIGAR "3M2I5M": all five representations upstream
      prints (RAW / SSAHA / EXT / SAM / SAMX) match the measured values.
  C6  diffstr_test over "10M1X10M": the SAM form normalises the X mismatch
      into 21M while the SAMX form preserves 10M1X10M - i.e. the
      DIFFSTRFORM_CIGEXT_XMISMATCH branch really differs from the plain one.

Expected values were measured on the unmodified upstream 0.7.6 sources built
natively (see notes.md); nothing here is guessed from file names or comments.

Nothing is copied, renamed or hard-linked before execution (only the binaries
the build actually produced are run), so the HarmonyOS .codesign execution
constraint is respected.  All scratch files go to --workdir, never /tmp
(read-only erofs on OHOS, E002).
"""
import argparse
import os
import subprocess
import sys

COMPLEMENT = str.maketrans("ACGTNacgtn", "TGCANtgcan")

CHECKS = ("C1", "C2", "C3", "C4", "C5", "C6")


def revcomp(seq):
    return seq.translate(COMPLEMENT)[::-1]


class Runner(object):
    def __init__(self, workdir):
        self.workdir = workdir
        self.passed = []
        self.failed = []

    def report(self, name, ok, detail):
        if ok:
            self.passed.append(name)
            print("PASS %s %s" % (name, detail))
        else:
            self.failed.append(name)
            print("FAIL %s %s" % (name, detail))
        sys.stdout.flush()

    def run(self, argv, name):
        """Run a harness; return (rc, combined output)."""
        try:
            proc = subprocess.run(argv, cwd=self.workdir, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, timeout=300)
            return proc.returncode, proc.stdout.decode("utf-8", "replace")
        except OSError as exc:
            self.report(name, False, "cannot execute %s: %s" % (argv[0], exc))
            return None, ""
        except subprocess.TimeoutExpired:
            self.report(name, False, "%s timed out" % os.path.basename(argv[0]))
            return None, ""

    def write(self, name, text, mode="w"):
        path = os.path.join(self.workdir, name)
        with open(path, mode) as fh:
            fh.write(text)
        return path

    def read(self, path):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except OSError as exc:
            return "<unreadable %s: %s>" % (path, exc)


def parse_fasta(text):
    """Return [(name, sequence)] from FASTA-ish output."""
    out = []
    name, chunks = None, []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if name is not None:
                out.append((name, "".join(chunks)))
            parts = line[1:].split()
            name = parts[0] if parts else line[1:]
            chunks = []
        else:
            chunks.append(line)
    if name is not None:
        out.append((name, "".join(chunks)))
    return out


def parse_fastq(text):
    """Return [(header, sequence, quality)] from FASTQ output."""
    lines = [ln.rstrip("\n") for ln in text.splitlines() if ln.strip() != ""]
    out = []
    for i in range(0, len(lines) - 3, 4):
        if not lines[i].startswith("@"):
            continue
        out.append((lines[i][1:], lines[i + 1], lines[i + 3]))
    return out


def check_revcomp_fasta(r, harness):
    records = [("r1", "ACGTACGTAA"), ("r2", "TTTTGGGGCC"),
               ("r3", "GATTACAGATTACANN")]
    src = "".join(">%s\n%s\n" % rec for rec in records)
    inp = r.write("c1_in.fa", src)
    outp = os.path.join(r.workdir, "c1_out.fa")
    rc, out = r.run([harness, inp, outp], "C1")
    if rc is None:
        return
    if rc != 0:
        r.report("C1", False, "rc=%d output=%s" % (rc, out.strip()[:200]))
        return
    problems = []
    if "Revese complement of %d sequences." % len(records) not in out:
        problems.append("count line missing/incorrect: %r" % out.strip()[:120])
    got = parse_fasta(r.read(outp))
    want = [(name, revcomp(seq)) for name, seq in records]
    if got != want:
        problems.append("records %r != expected %r" % (got, want))
    r.report("C1", not problems,
             "FASTA reverse complement of %d records (%s)"
             % (len(records), "; ".join(problems) if problems else "rc=0, count line and all sequences exact"))


def check_revcomp_fastq(r, harness):
    reads = [("q1", "ACGTACGTAA", "IIII$AAAAA"),
             ("q2", "TTTTGGGGCC", "!5AZaz09|~")]
    src = "".join("@%s\n%s\n+\n%s\n" % rec for rec in reads)
    inp = r.write("c2_in.fq", src)
    outp = os.path.join(r.workdir, "c2_out.fq")
    rc, out = r.run([harness, inp, outp], "C2")
    if rc is None:
        return
    if rc != 0:
        r.report("C2", False, "rc=%d output=%s" % (rc, out.strip()[:200]))
        return
    got = parse_fastq(r.read(outp))
    want = [(name, revcomp(seq), qual[::-1]) for name, seq, qual in reads]
    problems = []
    if got != want:
        problems.append("records %r != expected %r" % (got, want))
    if "Revese complement of %d sequences." % len(reads) not in out:
        problems.append("count line missing: %r" % out.strip()[:120])
    r.report("C2", not problems,
             "FASTQ reverse complement + reversed quality string (%s)"
             % ("; ".join(problems) if problems
                else "rc=0, sequences complemented and qualities reversed"))


def check_error_paths(r, harness):
    empty = r.write("c3_empty.fa", "")
    outp = os.path.join(r.workdir, "c3_out.fa")
    rc, out = r.run([harness, empty, outp], "C3")
    ok = rc is not None and rc != 0 and "wrong FASTQ/FASTA format" in out
    r.report("C3", bool(ok),
             "empty input rejected (rc=%s, message=%r)"
             % (rc, out.strip().splitlines()[-1][:100] if out.strip() else ""))

    missing = os.path.join(r.workdir, "c4_does_not_exist.fa")
    outp = os.path.join(r.workdir, "c4_out.fa")
    rc, out = r.run([harness, missing, outp], "C4")
    ok = rc is not None and rc != 0 and "could not open file" in out
    r.report("C4", bool(ok),
             "missing input rejected (rc=%s, message=%r)"
             % (rc, out.strip().splitlines()[-1][:100] if out.strip() else ""))


# diffstr_test prints five labelled representations of the parsed CIGAR.
# Values measured on unmodified upstream 0.7.6.
DIFFSTR_EXPECT = {
    "3M2I5M": [
        ("CIGAR_RAW", "(I:03|I:00|S:05|M:00)"),
        ("CIGAR_SSAHA", "M 3 I 2 M 5"),
        ("CIGAR_EXT", "3M2I5M"),
        ("CIGAR_SAM", "3M2I5M"),
        ("CIGAR_SAMX", "3M2I5M"),
    ],
    "10M1X10M": [
        ("CIGAR_RAW", "(S:10|S:10|M:00)"),
        ("CIGAR_SSAHA", "M 21"),
        ("CIGAR_EXT", "21M"),
        ("CIGAR_SAM", "21M"),
        ("CIGAR_SAMX", "10M1X10M"),
    ],
}


def check_diffstr(r, harness, cigstr, name):
    rc, out = r.run([harness, cigstr], name)
    if rc is None:
        return
    if rc != 0:
        r.report(name, False, "diffstr_test %s rc=%d output=%s"
                 % (cigstr, rc, out.strip()[:200]))
        return
    lines = {}
    for line in out.splitlines():
        parts = line.strip().split(None, 1)
        if parts:
            lines[parts[0]] = parts[1].strip() if len(parts) > 1 else ""
    problems = []
    for label, expected in DIFFSTR_EXPECT[cigstr]:
        got = lines.get(label)
        if got != expected:
            problems.append("%s: got %r want %r" % (label, got, expected))
    r.report(name, not problems,
             "diffstr_test %s -> %d representations (%s)"
             % (cigstr, len(DIFFSTR_EXPECT[cigstr]),
                "; ".join(problems) if problems else "RAW/SSAHA/EXT/SAM/SAMX all exact"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--test-dir", required=True,
                    help="directory holding the two upstream test programs")
    ap.add_argument("--workdir", required=True,
                    help="writable scratch directory (never /tmp on OHOS)")
    args = ap.parse_args()

    revcomp = os.path.join(args.test_dir, "sequenceReverseComplement_test")
    diffstr = os.path.join(args.test_dir, "diffstr_test")
    for path in (revcomp, diffstr):
        if not os.path.isfile(path):
            print("FAIL C0 upstream test program missing: %s" % path)
            print("RESULT: passed=0 failed=%d" % len(CHECKS))
            return 1

    os.makedirs(args.workdir, exist_ok=True)
    r = Runner(args.workdir)

    print("# upstream C test programs: %s, %s" % (revcomp, diffstr))
    check_revcomp_fasta(r, revcomp)
    check_revcomp_fastq(r, revcomp)
    check_error_paths(r, revcomp)
    check_diffstr(r, diffstr, "3M2I5M", "C5")
    check_diffstr(r, diffstr, "10M1X10M", "C6")

    missing = [c for c in CHECKS if c not in r.passed and c not in r.failed]
    for name in missing:
        r.report(name, False, "check did not report a result")
    print("RESULT: passed=%d failed=%d" % (len(r.passed), len(r.failed)))
    return 1 if r.failed else 0


if __name__ == "__main__":
    sys.exit(main())
