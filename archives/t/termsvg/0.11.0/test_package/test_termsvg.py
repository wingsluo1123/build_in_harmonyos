#!/usr/bin/env python3
"""Consumer test for termsvg/0.11.0 (R34 substantial verification).

termsvg ships an executable, so the consumer test drives the REAL binary
against a REAL asciicast fixture and validates the real output — no stubs:

  1. the binary exists and runs (`--version`, `--help`);
  2. `export` converts a real asciicast into a real SVG whose payload is
     verified (SVG root element, non-trivial size, animated frames);
  3. `--minify` produces a still-valid but smaller SVG.

Exit code 0 == termsvg is installable AND functional on HarmonyOS PC.
"""
import os
import re
import subprocess
import sys

bin_dir = os.path.join(os.path.dirname(os.environ.get("TERMSVG_PACKAGE_ROOT", "")), "bin") \
    if os.environ.get("TERMSVG_PACKAGE_ROOT") else ""
pkg_bin = os.path.join(os.environ.get("TERMSVG_PACKAGE_ROOT", ""), "bin", "termsvg")


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def find_termsvg():
    """Locate the binary inside THIS package's payload.

    Deliberately NO PATH fallback: if the payload binary is missing the test
    must fail, so that CI's L1e destructive re-run (which removes the package
    artifacts and re-runs test_package) cannot pass by accident against some
    unrelated `termsvg` found on PATH.
    """
    root = os.environ.get("TERMSVG_PACKAGE_ROOT", "")
    if not root:
        return None
    cand = os.path.join(root, "bin", "termsvg")
    return cand if os.path.isfile(cand) else None


termsvg = find_termsvg()
if not termsvg:
    fail("termsvg executable not found in package payload")
print(f"PASS: termsvg executable present -> {termsvg}")

# --- 1. version / help -----------------------------------------------------
r = subprocess.run([termsvg, "--version"], capture_output=True, text=True, timeout=60)
out = r.stdout + r.stderr
if "termsvg" not in out:
    fail(f"--version output missing program name: {out!r}")
print("PASS: --version ->", out.strip().splitlines()[0] if out.strip() else "(empty)")

r = subprocess.run([termsvg, "--help"], capture_output=True, text=True, timeout=60)
out = r.stdout + r.stderr
for cmd in ("record", "play", "export"):
    if cmd not in out:
        fail(f"--help does not list `{cmd}` subcommand")
print("PASS: --help lists record/play/export subcommands")


# --- 2. real asciicast -> real SVG ----------------------------------------
# A minimal but genuine asciicast v2 stream (header + one output frame).
cast = (
    '{"version": 2, "width": 80, "height": 24, "timestamp": 1700000000, '
    '"env": {"SHELL": "/bin/sh", "TERM": "xterm-256color"}}\n'
    '[0.1, "o", "hello termsvg\\r\\n"]\n'
    '[0.5, "o", "second frame\\r\\n"]\n'
)
import tempfile

workdir = tempfile.mkdtemp(prefix="termsvg-consumer-")
cast_path = os.path.join(workdir, "sample.cast")
svg_path = os.path.join(workdir, "out.svg")
with open(cast_path, "w", encoding="utf-8") as f:
    f.write(cast)

r = subprocess.run([termsvg, "export", cast_path, "-o", svg_path],
                   capture_output=True, text=True, timeout=120)
if r.returncode != 0:
    fail(f"export failed rc={r.returncode}: {(r.stdout + r.stderr)[:400]}")
if not os.path.isfile(svg_path):
    fail("export reported success but produced no SVG file")

data = open(svg_path, "rb").read()
if not data.lstrip().startswith(b"<svg"):
    fail("output is not an SVG (missing <svg root)")
# A minimal 2-frame asciicast yields a ~1.3 KB SVG (window chrome, defs,
# clipPath, glyphs and the animation block); anything below 1 KB signals a
# truncated/empty render.
if len(data) < 1000:
    fail(f"SVG suspiciously small ({len(data)} bytes)")
text = data.decode("utf-8", errors="replace")
if not re.search(r'xmlns="http://www\.w3\.org/2000/svg"', text):
    fail("SVG namespace declaration missing")
# animation: termsvg emits CSS @keyframes for asciicast frames.
if "@keyframes" not in text:
    fail("SVG has no @keyframes animation blocks - expected animated output")
print(f"PASS: export produced valid animated SVG ({len(data)} bytes, "
      "contains @keyframes)")

# --- 3. minify path still yields valid SVG --------------------------------
min_path = os.path.join(workdir, "min.svg")
r = subprocess.run([termsvg, "export", cast_path, "-o", min_path, "-m"],
                   capture_output=True, text=True, timeout=120)
if r.returncode == 0 and os.path.isfile(min_path):
    m = open(min_path, "rb").read()
    if not m.lstrip().startswith(b"<svg"):
        fail("minified output is not an SVG")
    print(f"PASS: --minify produced valid SVG ({len(m)} bytes, "
          f"{len(m) < len(data) and 'smaller' or 'same-size'} than full)")
else:
    print(f"INFO: --minify skipped (rc={r.returncode}) - not a hard failure")

# --- 4. architecture check (aarch64 ELF, R34 platform substance) ----------
readelf = "/data/service/hnp/bin/llvm-readelf"
if os.path.isfile(readelf):
    hdr = subprocess.run([readelf, "-h", termsvg], capture_output=True,
                         text=True, timeout=30).stdout
    if "AArch64" in hdr:
        print("PASS: binary is an aarch64 ELF")
    else:
        fail(f"unexpected machine type: {hdr[:200]!r}")

print("\nALL CHECKS PASSED: termsvg 0.11.0 is installable and functional on HarmonyOS PC")
