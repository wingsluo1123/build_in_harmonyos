#!/usr/bin/env python3
"""Consumer-side functional test for the packaged LAGAN 2.0 toolkit.

This script is launched by ``test_package/conanfile.py`` through Conan's
``self.run()`` so that it always inspects the *installed* package and never
the build tree.

Phase 1 ("tree", always executed)
    Every artifact that LAGAN 2.0 ships must be present in ``<pkg>/bin``:
    the 6 alignment binaries, the 17 compiled utilities under ``utils/``,
    the perl wrappers and the scoring matrices; the ELFs must also carry
    the executable bit.

Phase 2 ("--run", only when the target can execute)
    Smoke-run the packaged aarch64 ELFs and check they print the usage
    banner documented in the upstream README.  LAGAN's drivers locate
    their data through ``$LAGAN_DIR``, so the consumer exports it before
    launching them -- exactly what the recipe's ``package_info()`` does for
    a real consumer.

Exit code 0 = all assertions passed.  On failure the failing assertions
are printed and the process exits with 1.
"""
import argparse
import os
import subprocess
import sys

MAIN_BINARIES = ("anchors", "chaos", "order", "mlagan", "prolagan", "glocal")

UTILS = (
    "bin2mf", "bin2bl", "cextract", "cstat", "contigorder",
    "getbounds", "getcontigpos", "getlength", "getoverlap",
    "rc", "seqmerge", "scorealign", "scorecontigs",
    "fa2xfa", "Glue", "dotplot", "overlay",
)

PERL_SCRIPTS = (
    "lagan.pl", "slagan.pl", "slagan-mfa.pl", "rechaos.pl",
    "anal_gloc.pl", "xmfa2mfa.pl", "Utils.pm",
)

SCORING_DATA = ("nucmatrix.txt", "blosum62.txt", "blosum62s.txt")

USAGE_BANNER = {
    "chaos": "chaos queryfile dbasefile",
    "mlagan": "mlagan seqfile_1",
}


class Checker(object):
    def __init__(self):
        self.passed = 0
        self.failed = []

    def ok(self, condition, message):
        if condition:
            self.passed += 1
        else:
            self.failed.append(message)
        return condition


def check_tree(chk, bin_dir):
    for name in MAIN_BINARIES:
        path = os.path.join(bin_dir, name)
        chk.ok(os.path.isfile(path), "missing main binary bin/%s" % name)
    for name in UTILS:
        path = os.path.join(bin_dir, "utils", name)
        chk.ok(os.path.isfile(path), "missing compiled utility bin/utils/%s" % name)
    for name in PERL_SCRIPTS:
        path = os.path.join(bin_dir, name)
        chk.ok(os.path.isfile(path), "missing perl wrapper bin/%s" % name)
    for name in SCORING_DATA:
        path = os.path.join(bin_dir, name)
        present = os.path.isfile(path) and os.path.getsize(path) > 0
        chk.ok(present, "missing or empty scoring matrix bin/%s" % name)


def check_executables(chk, bin_dir):
    for name in MAIN_BINARIES:
        path = os.path.join(bin_dir, name)
        chk.ok(os.access(path, os.X_OK), "bin/%s is not executable" % name)
    for name in UTILS:
        path = os.path.join(bin_dir, "utils", name)
        chk.ok(os.access(path, os.X_OK), "bin/utils/%s is not executable" % name)


def run_smoke(chk, bin_dir, name):
    env = dict(os.environ)
    env["LAGAN_DIR"] = bin_dir
    try:
        proc = subprocess.run(
            [os.path.join(bin_dir, name)],
            capture_output=True, text=True, env=env, timeout=60,
        )
    except OSError as exc:
        chk.ok(False, "smoke test %s failed to start: %s" % (name, exc))
        return
    output = (proc.stdout or "") + (proc.stderr or "")
    chk.ok(
        USAGE_BANNER[name] in output,
        "smoke test %s: banner %r not found in %r"
        % (name, USAGE_BANNER[name], output[:200]),
    )


def main():
    parser = argparse.ArgumentParser(description="LAGAN 2.0 consumer package test")
    parser.add_argument("--bin-dir", required=True,
                        help="<package_folder>/bin of the installed lagan package")
    parser.add_argument("--run", action="store_true",
                        help="also execute the packaged binaries (native target only)")
    args = parser.parse_args()

    chk = Checker()
    check_tree(chk, args.bin_dir)
    check_executables(chk, args.bin_dir)

    if args.run:
        for name in sorted(USAGE_BANNER):
            run_smoke(chk, args.bin_dir, name)

    print("test_lagan: %d assertions passed, %d failed"
          % (chk.passed, len(chk.failed)))
    for message in chk.failed:
        print("  FAIL: %s" % message)
    return 1 if chk.failed else 0


if __name__ == "__main__":
    sys.exit(main())