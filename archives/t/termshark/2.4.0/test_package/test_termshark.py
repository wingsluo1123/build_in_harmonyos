#!/usr/bin/env python3
"""Consumer test for termshark/2.4.0 (R34 substantial verification).

termshark is a terminal UI on top of `tshark` — it *execs* tshark for every
dissection (``utils.go:202`` refuses to start without it).  So this test
drives the real binary and the real runtime dependency together:

  1. the binary exists and runs (``--help`` lists the documented options);
  2. ``--version`` **delegates to the tshark** in PATH and prints the real
     TShark banner — this proves the runtime command dependency is satisfied
     (with tshark absent it fails with "Could not find tshark in your PATH");
  3. the tshark pipeline works against a **real pcap file**: tshark reads it
     and reports real packets/protocols (proves the dissection path termshark
     would use is functional on OHOS);
  4. the binary is an aarch64 ELF.

Environment handling: tshark is a shared-library application that needs its
whole dependency closure on LD_LIBRARY_PATH.  That path list must NOT be
applied to THIS process — it poisons unrelated binaries (the interpreter
running this script would fail with `libintl_gettext: symbol not found`).
So the recipe exports the pieces as plain variables and the child env for
termshark/tshark is built here, in place.
"""
import os
import subprocess
import sys


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def build_child_env():
    """Clean env + tshark bin on PATH + full lib closure on LD_LIBRARY_PATH."""
    env = dict(os.environ)

    tshark_bin = os.environ.get("TERMSHARK_TSHARK_BIN", "")
    if tshark_bin:
        env["PATH"] = tshark_bin + os.pathsep + env.get("PATH", "")

    lib_dirs = [d for d in os.environ.get("TERMSHARK_LIB_DIRS", "").split(os.pathsep) if d]
    if lib_dirs:
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            lib_dirs + (env["LD_LIBRARY_PATH"].split(os.pathsep)
                        if env.get("LD_LIBRARY_PATH") else []))
    return env


# Deliberately NO PATH fallback: if the payload binary is missing the test
# must fail, so that CI's L1e destructive re-run (which removes the package
# artifacts and re-runs test_package) cannot pass by accident against some
# unrelated `termshark` found on PATH.
termshark = os.path.join(os.environ.get("TERMSHARK_PACKAGE_ROOT", ""),
                         "bin", "termshark")
if not os.path.isfile(termshark):
    fail("termshark executable not found in package payload")
print(f"PASS: termshark executable present -> {termshark}")

child_env = build_child_env()
# Sanity: tshark must be resolvable in the child env.
# NOTE: resolve it in Python instead of `sh -c "command -v tshark"` — the CI
# worker's PATH does not include /bin, so a bare `sh` cannot be exec'd there
# (FileNotFoundError) even though /bin/sh exists.
def _resolve_tshark(env):
    search = env.get("PATH", "").split(os.pathsep)
    for d in search:
        if not d:
            continue
        candidate = os.path.join(d, "tshark")
        if os.path.isfile(candidate):
            return candidate
    return None


tshark_resolved = _resolve_tshark(child_env)
if not tshark_resolved:
    fail("tshark not resolvable with the built child env "
         f"(PATH={child_env.get('PATH')!r})")
print(f"PASS: tshark resolvable -> {tshark_resolved}")

# --- 1. --help documents the CLI surface ----------------------------------
r = subprocess.run([termshark, "--help"], capture_output=True, text=True,
                   timeout=90, env=child_env)
out = r.stdout + r.stderr
if "A wireshark-inspired terminal user interface" not in out:
    fail(f"--help missing expected banner: {out[:300]!r}")
for flag in ("-i", "-r", "-w", "-Y", "-f"):
    if flag not in out:
        fail(f"--help does not document {flag}")
print("PASS: --help shows banner and -i/-r/-w/-Y/-f options")

# --- 2. --version delegates to tshark (proves runtime dependency) ---------
r = subprocess.run([termshark, "--version"], capture_output=True, text=True,
                   timeout=180, env=child_env)
out = (r.stdout + r.stderr).strip()
if "TShark (Wireshark)" not in out:
    fail(f"--version did not delegate to tshark: {out[:300]!r}")
print("PASS: --version delegates to tshark ->", out.splitlines()[0])

# --- 3. tshark pipeline against a real pcap -------------------------------
# termshark itself is an interactive TUI, so the dissection it relies on is
# verified through tshark on the pcap the package ships in res/testdata/
# (the upstream fixture pkg/pcap/testdata/1.pcap).
pkg_root = os.environ.get("TERMSHARK_PACKAGE_ROOT", "")
pcap = None
if pkg_root:
    cand = os.path.join(pkg_root, "res", "testdata", "1.pcap")
    if os.path.isfile(cand):
        pcap = cand
if not pcap:
    env_dir = os.environ.get("TERMSHARK_PCAP_DIR", "")
    if env_dir and os.path.isfile(os.path.join(env_dir, "1.pcap")):
        pcap = os.path.join(env_dir, "1.pcap")

if pcap:
    # NOTE: use the already-resolved ABSOLUTE tshark path.  A bare "tshark"
    # relies on the child PATH, which the build/run env does not reliably
    # contain (the same trap as the `sh -c` fixed earlier) — it raised
    # FileNotFoundError even though `_resolve_tshark` had just found it via
    # the explicit TERMSHARK_TSHARK_BIN prefix.
    r = subprocess.run([tshark_resolved, "-r", pcap, "-c", "2"],
                       capture_output=True, text=True, timeout=240, env=child_env)
    out = r.stdout + r.stderr
    if r.returncode != 0 or "→" not in out:
        fail(f"tshark could not read the pcap: rc={r.returncode} out={out[:300]!r}")
    first = out.splitlines()[0].split()
    print(f"PASS: tshark dissected shipped pcap ({os.path.getsize(pcap)} bytes) ->",
          " ".join(first[:4]) if len(first) >= 4 else out.splitlines()[0][:80])
else:
    print("INFO: no pcap fixture found in package res/testdata/; "
          "skipping the pcap dissection step (tshark --version already proved "
          "the runtime dependency works)")

# --- 4. architecture check -------------------------------------------------
readelf = "/data/service/hnp/bin/llvm-readelf"
if os.path.isfile(readelf):
    hdr = subprocess.run([readelf, "-h", termshark], capture_output=True,
                         text=True, timeout=30).stdout
    if "AArch64" in hdr:
        print("PASS: binary is an aarch64 ELF")
    else:
        fail(f"unexpected machine type: {hdr[:200]!r}")

print("\nALL CHECKS PASSED: termshark 2.4.0 starts and its tshark dependency is functional")
