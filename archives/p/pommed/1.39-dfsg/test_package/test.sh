#!/data/service/hnp/bin/bash
#
# pommed test_package — exercises the installed `pommed` daemon.
#
# Upstream ships no unit tests (the Makefile has no `check` target), so this
# scripted suite covers the daemon's observable command-line behaviour plus two
# HarmonyOS/aarch64-specific assertions.  It runs against the *installed*
# package (binary resolved through PATH via VirtualRunEnv).
set -u

PASS=0
FAIL=0

pass() { echo "PASS: $*"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $*"; FAIL=$((FAIL + 1)); }

expect_eq() { # <name> <expected> <actual>
  if [ "$2" = "$3" ]; then pass "$1"; else fail "$1 (expected '$2', got '$3')"; fi
}

expect_contains() { # <name> <needle> <haystack>
  case "$3" in
    *"$2"*) pass "$1" ;;
    *) fail "$1 (missing '$2' in: $3)" ;;
  esac
}

# ── locate the installed daemon ────────────────────────────────────────────
POM="$(command -v pommed 2>/dev/null || true)"
expect_eq "pommed is on PATH" "yes" "$([ -n "$POM" ] && echo yes || echo no)"
if [ -z "$POM" ]; then
  echo "RESULT: $PASS passed, $FAIL failed"
  exit 1
fi

# ── 1. -v prints the version banner and exits 0 ────────────────────────────
# Exercises getopt parsing + the version/exit path of main().
out="$("$POM" -v 2>&1)"; rc=$?
expect_eq "pommed -v exit status" "0" "$rc"
expect_contains "pommed -v version banner" "pommed v1.39 Apple laptops hotkeys handler" "$out"
expect_contains "pommed -v copyright line" "Julien BLACHE" "$out"

# ── 2. an unknown option is diagnosed and exits 1 ─────────────────────────
out="$("$POM" -Z 2>&1)"; rc=$?
expect_eq "pommed -Z exit status" "1" "$rc"
expect_contains "pommed -Z prints usage" "Usage:" "$out"
expect_contains "pommed -Z usage lists -f" "run in the foreground" "$out"
expect_contains "pommed -Z usage lists -d" "debug messages" "$out"

# ── 3. foreground start must abort at a startup gate ──────────────────────
# `-f` forces console logging, so the diagnostics land on stdout/stderr.
# Non-root runner  → the privilege gate fires (geteuid() != 0).
# Root runner      → the gate is bypassed and startup stops at machine
#                    identification (non-Apple DMI).  Both are real upstream
#                    startup gates; `timeout` guards against the daemon
#                    actually entering its event loop.
out="$(timeout 20 "$POM" -f 2>&1)"; rc=$?
expect_eq "pommed -f aborts at a startup gate" "1" "$rc"
case "$out" in
  *"pommed needs root privileges to operate"*|*"Unknown Apple machine"*|*"Unknown non-Apple machine"*)
    pass "pommed -f reports the failing startup gate" ;;
  *)
    fail "pommed -f did not report an expected startup gate: $out" ;;
esac

# ── 4. HarmonyOS / aarch64 platform assertions ────────────────────────────
# 4a. The daemon must be a native AArch64 ELF (OHOS PC target), not an
#     emulated/foreign-arch artefact.
machine="$(readelf -h "$POM" 2>/dev/null | awk -F: '/Machine:/ {gsub(/ /, "", $2); print $2}')"
expect_eq "pommed is a native AArch64 ELF" "AArch64" "$machine"

# 4b. The x86-only SMI backlight driver must have been compiled with its
#     non-x86 guard: on aarch64 the raw I/O-port primitives (outb/inb/iopl)
#     do not exist, so probe() reports the hardware as unsupported.  The
#     guard message is a string literal in .rodata, which makes the
#     platform adaptation verifiable rather than a silent no-op.
guarded="$(readelf -p .rodata "$POM" 2>/dev/null)"
case "$guarded" in
  *"requires x86 I/O port access"*)
    pass "x86-only backlight driver carries the non-x86 guard" ;;
  *)
    fail "x86-only backlight driver guard not present in .rodata" ;;
esac

# ── summary ───────────────────────────────────────────────────────────────
echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
