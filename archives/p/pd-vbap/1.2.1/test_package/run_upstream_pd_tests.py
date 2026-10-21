#!/usr/bin/env python3
"""Execute the upstream pd-vbap unit-test patches against the packaged externals.

Upstream ships ``unittests/*-unittest.pd`` as Pd patches that are driven by
``testtools/unit-test-frame`` -- an abstraction the upstream repository does
**not** ship (the patches are only runnable where the author's test tooling is
installed).  To run the upstream patches verbatim we provide that frame
ourselves (``upstream_pd_tests/testtools/unit-test-frame.pd``): it supplies the
inlet/outlet signature the patches connect to, echoes every message it receives
(``UNTEST: <name>``) and reports on load (``UNTEST-frame: frame-ready``).

Pass criteria, per upstream patch, are data-driven (no eyeballing):

  1. the patch loads in a real Pd host;
  2. every object it creates resolves, i.e. the host log shows no
     ``couldn't create`` (a sabotaged/missing external fails here);
  3. the patch's own loadbang -> message-graph reaches the frame, so the
     expected test name is echoed;
  4. the host reports no ``error``/``connection failed`` lines.

The numeric DSP behaviour of the same three externals (gain factors, speaker
table) is asserted by the libpd consumer test (``consumer_e2e.c``) that runs
next to this script; this one proves the upstream patches themselves run on the
packaged artifacts.
"""
import argparse
import os
import shutil
import subprocess
import sys

EXTERNALS = ("vbap", "rvbap", "define_loudspeakers")

# (label, upstream patch file, test name the patch feeds to the frame)
TESTS = (
    ("vbap", "vbap-unittest.pd", "vbap"),
    ("rvbap", "rvbap-unittest.pd", "rvbap-unittest"),
    ("define_loudspeakers", "define_loudspeakers-unittest.pd",
     "define-loudspeaker-unittest"),
)

# The patches run a live DSP engine, so pd never quits by itself: the run is
# bounded by this timeout and a kill is the normal, expected end of a test.
RUN_TIMEOUT = 60


def stage_libdir(work, externals_dir):
    """Materialise the ``vbap/<name>`` layout the upstream patches address.

    Both the upstream patches and the upstream installer arrange the externals
    inside a ``vbap/`` folder (``vbap/vbap``, ``vbap/define_loudspeakers``),
    while Conan installs them flat in ``lib/pd-externals``.
    """
    libdir = os.path.join(work, "libdir")
    shutil.rmtree(libdir, ignore_errors=True)
    os.makedirs(os.path.join(libdir, "vbap"))
    for name in EXTERNALS:
        src = os.path.join(externals_dir, name + ".pd_linux")
        if not os.path.isfile(src):
            raise SystemExit("packaged Pd external missing: %s" % src)
        shutil.copy(src, os.path.join(libdir, "vbap", name + ".pd_linux"))
    return libdir


def run_patch(pd_bin, externals_dir, tests_dir, libdir, work, patch_name):
    patch = os.path.join(tests_dir, patch_name)
    if not os.path.isfile(patch):
        return "", "upstream test patch not found: %s" % patch
    env = dict(os.environ)
    env["TMPDIR"] = work
    env["HOME"] = work
    cmd = [pd_bin, "-nogui", "-nosound",
           "-path", externals_dir, "-path", tests_dir, "-path", libdir,
           "-open", patch]
    try:
        proc = subprocess.run(cmd, cwd=work, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=RUN_TIMEOUT)
        out = proc.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or b"").decode("utf-8", "replace")
    except OSError as exc:
        return "", "cannot run Pd host: %s" % exc
    return out, ""


def verdict(out):
    """Return the list of problems found in a Pd host log."""
    problems = []
    low = out.lower()
    if "couldn't create" in low:
        problems.append("unresolved object ('couldn't create')")
    if "connection failed" in low:
        problems.append("patch connection failed")
    for line in out.splitlines():
        if "error" in line.lower() and "error(1)" not in line.lower():
            problems.append("host reported error: %s" % line.strip())
            break
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pd", required=True, help="path to the Pd host binary")
    ap.add_argument("--externals", required=True,
                    help="directory holding the packaged *.pd_linux")
    ap.add_argument("--tests", required=True,
                    help="upstream_pd_tests directory")
    ap.add_argument("--work", required=True, help="writable scratch directory")
    args = ap.parse_args()

    work = os.path.abspath(args.work)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    libdir = stage_libdir(work, args.externals)

    passed = 0
    for label, patch_name, expected in TESTS:
        out, fatal = run_patch(args.pd, args.externals, args.tests, libdir,
                               work, patch_name)
        with open(os.path.join(work, label + ".log"), "w") as fh:
            fh.write(out)
        problems = [fatal] if fatal else verdict(out)
        if not problems and ("UNTEST: " + expected) not in out:
            problems.append("patch never reached the frame (expected marker "
                            "'UNTEST: %s')" % expected)
        if problems:
            print("  [FAIL] %-22s %s" % (label, "; ".join(problems)))
            for line in out.splitlines()[-8:]:
                print("         | %s" % line)
        else:
            passed += 1
            print("  [PASS] %-22s upstream patch executed "
                  "(marker 'UNTEST: %s')" % (label, expected))

    print("upstream Pd unittests: %d/%d passed" % (passed, len(TESTS)))
    return 0 if passed == len(TESTS) else 1


if __name__ == "__main__":
    sys.exit(main())
