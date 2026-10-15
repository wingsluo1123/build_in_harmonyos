#!/usr/bin/env python3
"""run_testcases.py — differential test runner for kati's testcase/*.mk.

Faithful Python port of upstream's Go harness (run_test.go, TestKati +
runMake + runKati + check + outputFiles + uniqueTestcases +
isExpectedFailure + the normalize* regex sets), limited to the
non-ninja / non-rkati path — OHOS has neither ninja nor Go.

Semantics preserved exactly:
  * each testcase/*.mk is written to two sandbox dirs (make-side and
    kati-side) as "Makefile", with a `submake` symlink to the testcase
    submake dir (upstream: "../../../testcase/submake");
  * make side:   make [-s] [tc] SHELL=<shell>        (CombinedOutput)
  * kati side:   ckati --use_find_emulator [-s] SHELL=<shell> [tc]
                 (CombinedOutput, 30 s timeout);
  * outputs are normalized with the same regex chains (normalizeMakeLog
    for make, normalizeKati for kati), then compared for equality;
  * files created on each side are listed with the same ignore rules and
    compared as symmetric difference (contents are NOT compared, same as
    upstream);
  * `# TODO` / `# TODO(all)[/tc|tc]` header markers pin expected
    failures (xfail): for xfail cases output MUST differ; xfail cases
    skip the file-list comparison;
  * --xfail-file (portability extension, not in run_test.go): one
    `<name>[ testN...] <reason...>` per line. Bare `<name>` pins the
    whole file; trailing `testN` tokens (exact "test" + digits) pin
    individual testcases of partially-failing files; the rest of the
    line is a free-text reason. A pinned case that comes out equal
    counts as XPASS and fails the run (same strictness as the upstream
    TODO semantics);
  * if the make side output contains "FAIL", the harness itself fails
    (upstream behavior — it means the reference run went wrong).

Port note (2026-10-08, Windows): translated line-by-line from
run_test.go @ ec1814e15fd4; regexes keep identical patterns with RE2 →
Python syntax adjustments only where required (no flag differences).
Portability (OHOS): sandbox workdir is caller-supplied (device /tmp is
read-only); testcase/submake is symlinked with a copy fallback for
filesystems without symlink support.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

TESTCASE_RE = re.compile(r"^test\d*")
TODO_RE = re.compile(r"^# TODO(?:\(([-a-z|]+)(?:/([-a-z0-9|]+))?\))?")

# --- normalization chains (port of run_test.go normalize*) ---

def _norm(pattern, replace):
    return (re.compile(pattern), replace)

# Go/RE2 works on bytes: `\xe2\x80\x98` is the UTF-8 sequence for U+2018.
# Python operates on str, so use the codepoints themselves.
NORMALIZE_QUOTES = _norm("([`'\"]|‘|’)", '"')

NORMALIZE_MAKE_LOG = [
    NORMALIZE_QUOTES,
    _norm(r"make(?:\[\d+\])?: (Entering|Leaving) directory[^\n]*\n", ""),
    _norm(r"make(?:\[\d+\])?: ", ""),
    # Normalizations for old/new GNU make.
    _norm(" recipe for target ", " commands for target "),
    _norm(" recipe commences ", " commands commence "),
    _norm(r"missing rule before recipe\.", "missing rule before commands."),
    _norm(r" (did you mean TAB instead of 8 spaces?)", ""),
    _norm(r"Extraneous text after", "extraneous text after"),
    _norm(r"\s+Stop\.", ""),
    _norm(r'Makefile:\d+: commands for target ".*?" failed\n', ""),
    _norm(r"/bin/(ba)?sh: line 1: ", ""),
    _norm(r'(: \S+: No such file or directory)\n\*\*\* No rule to make target "[^"]+".', r"\1"),
    _norm(r"\[\S+:\d+: ", "["),
]

NORMALIZE_MAKE_NINJA = _norm(r"ninja: warning: [^\n]+", "")

NORMALIZE_KATI = [
    NORMALIZE_QUOTES,
    _norm(r"\*kati\*[^\n]*", ""),
    _norm(r"c?kati: ", ""),
    _norm(r"/bin/(ba)?sh: line 1: ", ""),
    _norm(r"/bin/sh: ", ""),
    _norm(r".*: warning for parse error in an unevaluated line: [^\n]*", ""),
    _norm(r"([^\n ]+: )?FindEmulator: ", ""),
    _norm(r" (\./+)+kati\.\S+", ""),
    _norm(r" (\./+)+test\S+\.json", ""),
    _norm(r"(: )open (\S+): n(o such file or directory)\nNOTE:[^\n]*", r"\1\2: N\3"),
    # Bionic/musl libc error wording differs from glibc (upstream comment)
    _norm(r"Too many symbolic links encountered", "Too many levels of symbolic links"),
    _norm(r" \(os error \d+\)", ""),
]

# OHOS portability (device evidence, 2026-10-09): bash 5.3 on OHOS emits
# getcwd fallback noise ("shell-init:/chdir: error retrieving current
# directory: getcwd: ...") into command output on both the make and the
# kati side; the line count varies with the subshell environment (observed
# flipping find_command.mk[test1] between runs). It carries zero
# make-vs-kati information — strip it from both chains, same category as
# upstream's "Entering/Leaving directory" removal. No-op on platforms
# where getcwd works (upstream CI, musl containers).
NOISE_CWD = _norm(
    r"(?m)^(?:shell-init|chdir): error retrieving current directory: .*$\n?", "")

NORMALIZE_MAKE_LOG.append(NOISE_CWD)
NORMALIZE_KATI.append(NOISE_CWD)


CIRCULAR_RE = re.compile(r"(Circular .* dropped\.\n)")


def normalize(text, norms):
    # Upstream normalize(): "We don't care when circular dependency
    # detection happens" — pull all Circular lines out, strip them from
    # the log, then prepend, so detection order differences don't count.
    circ = CIRCULAR_RE.findall(text)
    text = "".join(circ) + CIRCULAR_RE.sub("", text)
    for rx, repl in norms:
        text = rx.sub(repl, text)
    return text


def unique_testcases(content):
    seen = set()
    ret = []
    for line in content.split("\n"):
        s = TESTCASE_RE.search(line)
        if not s:
            continue
        s = s.group(0)
        if s in seen:
            continue
        seen.add(s)
        ret.append(s)
    ret.sort()
    return ret if ret else [""]


TC_TOKEN_RE = re.compile(r"test\d*")


def parse_xfail_file(path):
    """-> {name: None (whole file) | frozenset(tcs)}"""
    xf = {}
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                tokens = line.split()
                tcs = frozenset(t for t in tokens[1:]
                                if TC_TOKEN_RE.fullmatch(t))
                xf[tokens[0]] = tcs or None
    return xf


def is_expected_failure(content, tc):
    for line in content.split("\n"):
        if not (line.startswith("#!") or line.startswith("# TODO")):
            break
        todo = TODO_RE.match(line)
        if todo is None:
            continue
        modes = todo.group(1)
        tcs = todo.group(2)
        if modes is None:
            return True  # bare "# TODO"
        todo_list = modes.split("|")
        # non-ninja port: "ninja"/"ninja-genall" markers never match; "all" does
        if "all" in todo_list:
            if tcs is None:
                return True
            if tc in tcs.split("|"):
                return True
    return False


IGNORE_FILES = {
    ".", "..", "Makefile", "build.ninja", "env.sh", "ninja.sh",
    "gmon.out", "submake",
}


def output_files(d):
    ret = []
    for name in sorted(os.listdir(d)):
        if (name in IGNORE_FILES or name.startswith(".") or
                name.endswith(".json") or name.startswith("kati") or
                name.startswith("stdout")):
            continue
        ret.append(name)
    return ret


def diff_lists(a, b):
    only_a = [x for x in a if x not in b]
    only_b = [x for x in b if x not in a]
    return only_a, only_b


def run(cmd, cwd, timeout):
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return proc.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode("utf-8", "replace")
        return out + "\nRUNNER-TIMEOUT\n"


def setup_case_dir(base, content, testcase_dir):
    if os.path.exists(base):
        shutil.rmtree(base)
    os.makedirs(base)
    with open(os.path.join(base, "Makefile"), "w", newline="") as f:
        f.write(content)
    # Upstream symlinks testcase/submake into the sandbox. Some OHOS
    # filesystems do not support symlinks: fall back to a sandbox-local
    # copy (semantically identical — make just resolves the path).
    try:
        os.symlink(
            os.path.join(testcase_dir, "submake"),
            os.path.join(base, "submake"),
            target_is_directory=True,
        )
    except OSError:
        shutil.copytree(
            os.path.join(testcase_dir, "submake"),
            os.path.join(base, "submake"),
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckati", required=True, help="path to ckati binary")
    ap.add_argument("--shell", required=True,
                    help="SHELL passed to both sides (OHOS: CONFIG_SHELL)")
    ap.add_argument("--testcase-dir", default="testcase")
    ap.add_argument("--workdir", default=None,
                    help="scratch dir (default: <tmp>/kati-diff-<pid>)")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--xfail-file", default=None,
                    help="optional file: one '<name>[ testN...] <reason>' "
                         "per line; bare <name> pins the whole file, "
                         "trailing testN tokens pin individual tcs")
    ap.add_argument("--only", default=None,
                    help="comma-separated subset of testcase names")
    args = ap.parse_args()

    xfail_platform = parse_xfail_file(args.xfail_file)

    only = set(args.only.split(",")) if args.only else None
    tc_dir = os.path.abspath(args.testcase_dir)
    work = args.workdir or os.path.join(
        tempfile.gettempdir(), "kati-diff-%d" % os.getpid())
    os.makedirs(work, exist_ok=True)

    ckati = os.path.abspath(args.ckati)
    names = sorted(n for n in os.listdir(tc_dir) if n.endswith(".mk"))
    if only:
        names = [n for n in names if n in only]

    npass = nfail = nxfail = nxpass = 0
    failures = []
    xpins = []
    for name in names:
        with open(os.path.join(tc_dir, name), encoding="utf-8") as f:
            content = f.read()
        tcs = unique_testcases(content)
        is_silent = name.startswith("submake_")
        # Upstream layout (run_test.go:422-455): ONE sandbox pair per FILE,
        # out/<name>/{make,kati} — sibling dirs sharing the parent, and ALL
        # testcases of the file run SEQUENTIALLY in the same dir (test1's
        # touched files are visible to test2, e.g. order_only2.mk). Run
        # order also mirrors upstream: all make-side runs first, then all
        # kati-side runs, then per-tc checks.
        d_parent = os.path.join(work, name)
        d_make = os.path.join(d_parent, "make")
        d_kati = os.path.join(d_parent, "kati")
        try:
            setup_case_dir(d_make, content, tc_dir)
            setup_case_dir(d_kati, content, tc_dir)
        except OSError as e:
            # symlink 未支持等沙箱限制：该文件整体跳过并计数(如实报告)
            for tc in tcs:
                nfail += 1
                failures.append((name, tc, "SETUP-ERROR: %s" % e))
            continue

        expected = {}
        expected_files = {}
        expected_failures = {}
        got = {}
        got_files = {}

        for tc in tcs:
            make_args = ["make"]
            if is_silent:
                make_args.append("-s")
            if tc:
                make_args.append(tc)
            make_args.append("SHELL=" + args.shell)
            m_raw = run(make_args, d_make, args.timeout * 3)
            m = normalize(m_raw, NORMALIZE_MAKE_LOG)
            m = normalize(m, [NORMALIZE_MAKE_NINJA])
            expected[tc] = m
            expected_files[tc] = output_files(d_make)
            expected_failures[tc] = is_expected_failure(content, tc) or \
                (name in xfail_platform and
                 (xfail_platform[name] is None or tc in xfail_platform[name]))

        for tc in tcs:
            kati_args = [ckati, "--use_find_emulator"]
            if is_silent:
                kati_args.append("-s")
            kati_args.append("SHELL=" + args.shell)
            if tc:
                kati_args.append(tc)
            k_raw = run(kati_args, d_kati, args.timeout)
            k = normalize(k_raw, NORMALIZE_KATI)
            got[tc] = k
            got_files[tc] = output_files(d_kati)

        for tc in tcs:
            m = expected[tc]
            k = got[tc]
            m_files = expected_files[tc]
            k_files = got_files[tc]
            if "FAIL" in m:
                nfail += 1
                failures.append((name, tc, "MAKE-SIDE-FAIL"))
                continue
            if expected_failures[tc]:
                if m == k:
                    nxpass += 1
                    xpins.append((name, tc, "xfail but outputs match"))
                else:
                    nxfail += 1
                continue
            if m != k:
                nfail += 1
                failures.append((name, tc, "OUTPUT-DIFF"))
                continue
            only_m, only_k = diff_lists(m_files, k_files)
            if only_m or only_k:
                nfail += 1
                failures.append((name, tc,
                                 "FILES make-only=%s kati-only=%s" % (only_m, only_k)))
                continue
            npass += 1

    total = npass + nfail + nxfail + nxpass
    print("kati differential suite: total=%d pass=%d fail=%d "
          "xfail=%d xpass=%d" % (total, npass, nfail, nxfail, nxpass))
    if xpins:
        print("XFails that now match (unpin them):")
        for name, tc, why in xpins:
            print("  XPASS %s[%s]: %s" % (name, tc or "default", why))
    if failures:
        print("Failures:")
        for name, tc, why in failures:
            print("  FAIL %s[%s]: %s" % (name, tc or "default", why))
    rc = 0 if (not failures and not xpins) else 1
    sys.exit(rc)


if __name__ == "__main__":
    main()
