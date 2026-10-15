#!/usr/bin/env python3
"""On-device consumer suite for the packaged smalt 0.7.6 binaries.

Runs only where the packaged aarch64-linux-ohos ELF can actually execute, i.e.
on the HarmonyOS worker (test_package/conanfile.py gates it with can_run()).
Every check drives the *installed* product through its real CLI - nothing is
copied, renamed or hard-linked first, because HarmonyOS refuses to execute an
ELF that has been moved across the .codesign signing boundary - and every
scratch file goes under --workdir, never /tmp (read-only erofs on OHOS, E002).

Two groups, both counted in test_package/MANIFEST.yml:

F1-F8  functional consumer checks over the documented CLI surface.  They are
       not HarmonyOS specific, but they prove the cross-compiled package really
       indexes a reference, aligns reads and reports the correct SAM records.

H1-H5  HarmonyOS specific runtime checks.  Each one pins a platform behaviour
       that this adaptation had to get right: executing the signed installed
       product (H1), the statically linked zlib working on musl for gzipped
       references (H2), pthread/semaphore based multi-threaded mapping staying
       deterministic on musl (H3), index files living on HMDFS-backed storage
       and being re-readable by a second process (H4), and musl's rand()/
       srand48() reproducing the same alignments run after run (H5).

Expected values were measured on the unmodified upstream 0.7.6 sources; see
case_gen.py for the deterministic input case and notes.md for the measurements.
Exit code 0 = every check passed.
"""
import argparse
import gzip
import os
import shutil
import subprocess
import sys

import case_gen

TASKS = ("check", "help", "index", "map", "sample", "version")


class Suite(object):
    def __init__(self, bindir, workdir):
        self.bindir = bindir
        self.workdir = workdir
        self.passed = []
        self.failed = []
        os.makedirs(workdir, exist_ok=True)

    def tool(self, name):
        return os.path.join(self.bindir, name)

    def run(self, argv, timeout=600):
        """Run an installed binary; return (rc, combined stdout+stderr)."""
        try:
            proc = subprocess.run(argv, cwd=self.workdir,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, timeout=timeout)
            return proc.returncode, proc.stdout.decode("utf-8", "replace")
        except OSError as exc:
            return None, "cannot execute %s: %s" % (argv[0], exc)
        except subprocess.TimeoutExpired:
            return None, "%s timed out after %ss" % (os.path.basename(argv[0]), timeout)

    def report(self, name, ok, detail):
        if ok:
            self.passed.append(name)
            print("PASS %s %s" % (name, detail))
        else:
            self.failed.append(name)
            print("FAIL %s %s" % (name, detail))
        sys.stdout.flush()

    def path(self, name):
        return os.path.join(self.workdir, name)


def parse_sam(text):
    """Return (headers, {qname: (flag, rname, pos, mapq, cigar, nm, as_)})."""
    headers, records = [], {}
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.startswith("@"):
            headers.append(line)
            continue
        f = line.split("\t")
        if len(f) < 11:
            continue
        nm = as_ = None
        for tag in f[11:]:
            if tag.startswith("NM:i:"):
                nm = int(tag[5:])
            elif tag.startswith("AS:i:"):
                as_ = int(tag[5:])
        records[f[0]] = (int(f[1]), f[2], int(f[3]), int(f[4]), f[5], nm, as_)
    return headers, records


def sam_body(text):
    """SAM alignment lines only, sorted by query name (thread order is not
    preserved upstream, and @PG embeds the command line)."""
    return sorted(ln for ln in text.splitlines()
                  if ln.strip() and not ln.startswith("@"))


# ---------------------------------------------------------------- F checks
def f1_help(s):
    rc, out = s.run([s.tool("smalt"), "help"])
    missing = [t for t in TASKS if t not in out]
    ok = rc == 0 and "Sequence Mapping and Alignment Tool" in out and not missing
    s.report("F1", ok, "`smalt help` rc=%s, banner and %d task names present%s"
             % (rc, len(TASKS), "" if not missing else ", missing %s" % missing))


def f2_no_args(s):
    rc, out = s.run([s.tool("smalt")])
    ok = rc == 51 and "SYNOPSIS:" in out
    s.report("F2", ok, "`smalt` with no arguments rc=%s (upstream 51) and prints SYNOPSIS" % rc)


def f3_unknown_task(s):
    rc, out = s.run([s.tool("smalt"), "bogus"])
    ok = rc == 51 and "ERROR: unknown task switch bogus" in out
    s.report("F3", ok, "unknown task rejected rc=%s, message=%r"
             % (rc, out.strip().splitlines()[0][:70] if out.strip() else ""))


def f4_task_help(s):
    problems = []
    for task in ("index", "map"):
        rc, out = s.run([s.tool("smalt"), task, "-H"])
        if rc != 0 or "SYNOPSIS:" not in out:
            problems.append("%s -H rc=%s synopsis=%s" % (task, rc, "SYNOPSIS:" in out))
    s.report("F4", not problems,
             "per-task help for index/map (%s)" % ("; ".join(problems) if problems else "both rc=0 with SYNOPSIS"))


def f5_check_reads(s, case):
    rc, out = s.run([s.tool("smalt"), "check", case["reads_fq"]])
    want = "checked %d reads: ok." % case["read_count"]
    ok = rc == 0 and want in out
    s.report("F5", ok, "`smalt check` rc=%s, %r" % (rc, out.strip().splitlines()[-1][:70] if out.strip() else ""))


def f6_index_and_map(s, case, index, sam_path):
    rc, out = s.run([s.tool("smalt"), "index", "-k", str(case_gen.KMER),
                     "-s", str(case_gen.NSKIP), index, case["ref_fa"]])
    if rc != 0:
        s.report("F6", False, "`smalt index` rc=%s: %s" % (rc, out.strip()[-300:]))
        return None
    rc, out = s.run([s.tool("smalt"), "map", "-f", "sam", "-r", str(case_gen.MAP_SEED),
                     "-o", sam_path, index, case["reads_fq"]])
    if rc != 0:
        s.report("F6", False, "`smalt map` rc=%s: %s" % (rc, out.strip()[-300:]))
        return None
    with open(sam_path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    headers, records = parse_sam(text)
    problems = []
    for qname, flag, pos, cigar, nm, as_ in case_gen.EXPECTED_ALIGNMENTS:
        got = records.get(qname)
        if got is None:
            problems.append("%s absent" % qname)
            continue
        if (got[0], got[2], got[4], got[5], got[6]) != (flag, pos, cigar, nm, as_):
            problems.append("%s got flag/pos/cigar/NM/AS=%s want %s"
                            % (qname, (got[0], got[2], got[4], got[5], got[6]),
                               (flag, pos, cigar, nm, as_)))
        if got[1] != case_gen.REF_NAME:
            problems.append("%s rname=%s" % (qname, got[1]))
        if not 0 <= got[3] <= 60:
            problems.append("%s mapq out of range: %s" % (qname, got[3]))
    sq = [h for h in headers if h.startswith("@SQ")]
    if not sq or "SN:%s" % case_gen.REF_NAME not in sq[0] \
            or "LN:%d" % case_gen.REF_LEN not in sq[0]:
        problems.append("@SQ header wrong: %s" % (sq[:1],))
    pg = [h for h in headers if h.startswith("@PG")]
    if not pg:
        problems.append("@PG header missing")
    elif "VN:0.7.6" not in pg[0]:
        problems.append("@PG version wrong: %s" % pg[0][:80])
    s.report("F6", not problems,
             "index+map end to end: %d reads aligned (%s)"
             % (len(case_gen.EXPECTED_ALIGNMENTS),
                "; ".join(problems) if problems
                else "flag/POS/CIGAR/NM/AS all match the measured upstream values"))
    return text


def f7_unmapped(s, case, index):
    out_sam = s.path("mixed.sam")
    rc, out = s.run([s.tool("smalt"), "map", "-f", "sam", "-r", str(case_gen.MAP_SEED),
                     "-o", out_sam, index, case["mixed_fq"]])
    if rc != 0:
        s.report("F7", False, "`smalt map` over the mixed read set rc=%s" % rc)
        return
    with open(out_sam, encoding="utf-8", errors="replace") as fh:
        _headers, records = parse_sam(fh.read())
    got = records.get(case_gen.UNMAPPED_NAME)
    ok = got is not None and got[0] == 4 and got[1] == "*" and got[2] == 0 and got[4] == "*"
    s.report("F7", bool(ok),
             "unmappable read reported as unmapped (%s)"
             % ("flag=4 RNAME=* POS=0 CIGAR=*" if ok else "got %r" % (got,)))


def f8_misc_tools(s, case, index):
    problems = []
    rc, out = s.run([s.tool("readstats"), case["reads_fq"]])
    lines = [ln for ln in out.splitlines() if ln.strip()]
    if rc != 0 or len(lines) != case["read_count"]:
        problems.append("readstats rc=%s lines=%d (want %d)"
                        % (rc, len(lines), case["read_count"]))
    else:
        for name, seq, _strand, _off in case_gen.reads():
            if "%s %d" % (name, len(seq)) not in out:
                problems.append("readstats missing '%s %d'" % (name, len(seq)))
    rc, out = s.run([s.tool("fetchseq"), index, case_gen.REF_NAME,
                     str(case_gen.FETCHSEQ_POS), str(case_gen.FETCHSEQ_LEN)])
    want = case_gen.fetchseq_expected()
    if rc != 0 or want not in out:
        problems.append("fetchseq rc=%s, expected window %s present=%s"
                        % (rc, want, want in out))
    s.report("F8", not problems,
             "companion tools readstats + fetchseq (%s)"
             % ("; ".join(problems) if problems
                else "%d read-length lines and the exact %d bp reference window"
                    % (case["read_count"], case_gen.FETCHSEQ_LEN)))


# ---------------------------------------------------------------- H checks
def h1_installed_product_runs(s):
    binary = s.tool("smalt")
    rc, out = s.run([binary, "version"])
    ok = rc == 0 and "Version: 0.7.6" in out
    s.report("H1", ok,
             "the signed installed ELF executes in place (%s): rc=%s, %r"
             % (binary, rc,
                out.strip().splitlines()[1][:60] if len(out.strip().splitlines()) > 1 else out.strip()[:60]))


def h2_gzip_input(s, case, sam_plain):
    """HAVE_ZLIB path: the statically linked zlib must decompress on musl."""
    gz_path = s.path("ref.fa.gz")
    with open(case["ref_fa"], "rb") as src, gzip.open(gz_path, "wb") as dst:
        shutil.copyfileobj(src, dst)
    index = s.path("idxgz")
    rc, out = s.run([s.tool("smalt"), "index", "-k", str(case_gen.KMER),
                     "-s", str(case_gen.NSKIP), index, gz_path])
    if rc != 0:
        s.report("H2", False, "`smalt index` on a gzipped reference rc=%s: %s"
                 % (rc, out.strip()[-200:]))
        return
    sam_gz = s.path("outgz.sam")
    rc, out = s.run([s.tool("smalt"), "map", "-f", "sam", "-r", str(case_gen.MAP_SEED),
                     "-o", sam_gz, index, case["reads_fq"]])
    if rc != 0:
        s.report("H2", False, "`smalt map` from the gzipped-reference index rc=%s" % rc)
        return
    with open(sam_gz, encoding="utf-8", errors="replace") as fh:
        gz_text = fh.read()
    same = sam_body(gz_text) == sam_body(sam_plain)
    s.report("H2", same,
             "gzipped reference through statically linked zlib on musl: "
             "%d alignment lines %s the uncompressed-index run"
             % (len(sam_body(gz_text)), "identical to" if same else "DIFFER from"))


def h3_threads(s, case, index, sam_plain):
    """threads.c uses pthreads + unnamed POSIX semaphores; musl must agree
    with the single-threaded result.  Upstream documents that read order is not
    preserved with -n, so the comparison is order-insensitive."""
    sam_mt = s.path("outmt.sam")
    rc, out = s.run([s.tool("smalt"), "map", "-f", "sam", "-n", "4",
                     "-r", str(case_gen.MAP_SEED), "-o", sam_mt, index,
                     case["reads_fq"]])
    if rc != 0:
        s.report("H3", False, "`smalt map -n 4` rc=%s: %s" % (rc, out.strip()[-200:]))
        return
    with open(sam_mt, encoding="utf-8", errors="replace") as fh:
        mt_text = fh.read()
    single, multi = sam_body(sam_plain), sam_body(mt_text)
    same = single == multi
    detail = "%d records with -n 4 vs %d with -n 1" % (len(multi), len(single))
    if not same:
        for a, b in zip(single, multi):
            if a != b:
                detail += "; first difference:\n  -n1: %s\n  -n4: %s" % (a[:110], b[:110])
                break
    s.report("H3", same,
             "multi-threaded mapping (pthread + sem_t on OHOS musl) %s"
             % ("matches the single-threaded alignment set" if same else "DIFFERS: " + detail))


def h4_index_files_on_device_storage(s, case, index):
    """HMDFS/sandbox filesystem semantics: the index pair is created in the
    writable directory the caller chose (never /tmp), is non-empty, and is
    re-readable by a *second* process."""
    problems = []
    for ext in (".smi", ".sma"):
        path = index + ext
        if not os.path.isfile(path):
            problems.append("%s missing" % path)
            continue
        size = os.path.getsize(path)
        if size <= 0:
            problems.append("%s is empty" % path)
        if not os.path.abspath(path).startswith(os.path.abspath(s.workdir)):
            problems.append("%s escaped the workdir" % path)
    if not problems:
        probe = s.path("reopen.sam")
        rc, out = s.run([s.tool("smalt"), "map", "-f", "sam",
                         "-r", str(case_gen.MAP_SEED), "-o", probe, index,
                         case["reads_fq"]])
        if rc != 0 or not os.path.isfile(probe) or os.path.getsize(probe) == 0:
            problems.append("a second process could not reuse the index (rc=%s)" % rc)
    s.report("H4", not problems,
             "index .smi/.sma written to the caller-chosen writable dir "
             "(%d and %d bytes) and reusable by a second process%s"
             % (os.path.getsize(index + ".smi") if os.path.isfile(index + ".smi") else -1,
                os.path.getsize(index + ".sma") if os.path.isfile(index + ".sma") else -1,
                "" if not problems else "; " + "; ".join(problems)))


def h5_rng_reproducibility(s, case, index):
    """smalt seeds rand()/srand48 from time(0) unless -r is given, and musl's
    generators are not glibc's.  With a fixed seed three consecutive runs of the
    installed binary must be byte-identical."""
    bodies = []
    for i in range(3):
        out_sam = s.path("rep%d.sam" % i)
        rc, _out = s.run([s.tool("smalt"), "map", "-f", "sam",
                          "-r", str(case_gen.MAP_SEED), "-o", out_sam, index,
                          case["reads_fq"]])
        if rc != 0:
            s.report("H5", False, "run %d rc=%s" % (i + 1, rc))
            return
        with open(out_sam, encoding="utf-8", errors="replace") as fh:
            bodies.append(sam_body(fh.read()))
    same = bodies[0] == bodies[1] == bodies[2]
    s.report("H5", same,
             "3 consecutive `smalt map -r %d` runs on OHOS musl are %s (%d records each)"
             % (case_gen.MAP_SEED, "byte-identical" if same else "NOT identical",
                len(bodies[0])))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bindir", required=True, help="bin/ of the tested package")
    ap.add_argument("--workdir", required=True, help="writable scratch dir (not /tmp)")
    args = ap.parse_args()

    s = Suite(args.bindir, args.workdir)
    binary = s.tool("smalt")
    if not os.path.isfile(binary):
        print("FAIL F0 packaged binary missing: %s" % binary)
        print("RESULT: passed=0 failed=13")
        return 1

    print("# smalt on-device consumer suite")
    print("# bindir=%s" % args.bindir)
    print("# workdir=%s" % args.workdir)
    case = case_gen.write_case(args.workdir)

    f1_help(s)
    f2_no_args(s)
    f3_unknown_task(s)
    f4_task_help(s)
    f5_check_reads(s, case)

    index = s.path("idx")
    sam_plain = s.path("out.sam")
    sam_text = f6_index_and_map(s, case, index, sam_plain)
    f7_unmapped(s, case, index)
    f8_misc_tools(s, case, index)

    h1_installed_product_runs(s)
    if sam_text:
        h2_gzip_input(s, case, sam_text)
        h3_threads(s, case, index, sam_text)
    else:
        s.report("H2", False, "skipped: F6 produced no SAM output")
        s.report("H3", False, "skipped: F6 produced no SAM output")
    h4_index_files_on_device_storage(s, case, index)
    h5_rng_reproducibility(s, case, index)

    print("RESULT: passed=%d failed=%d" % (len(s.passed), len(s.failed)))
    return 1 if s.failed else 0


if __name__ == "__main__":
    sys.exit(main())
