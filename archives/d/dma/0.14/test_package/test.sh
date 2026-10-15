#!/data/service/hnp/bin/bash
# test_package/test.sh — dma 0.14 consumer assertions (2 assertions).
#
# Both assertions stay inside getopt()'s argument stage, upstream of
# parse_conf() at dma.c:606, so neither touches /etc/dma.conf, the spool or
# the delivery path. Expected exit code is EX_USAGE (sysexits.h == 64);
# this run prints the observed value so the number can be pinned from the log.
# Security modes per code-style §7: `set -euo pipefail`. Both assertions
# deliberately capture a *non-zero* dma exit status, so each capture is written
# as `out=$(cmd) || rc=$?` — that keeps `set -e` satisfied (the OR-list always
# succeeds) while still storing dma's real exit code in `$rc` (a bare
# `|| true` would make `$?` become 0 and silently lose the observed status).
# Failures are aggregated in `$fail` (non-zero ⇒ exit 1 below).
set -euo pipefail

fail=0

if ! command -v dma >/dev/null 2>&1; then
    echo "❌ dma not on PATH (VirtualRunEnv did not expose bindirs)"
    exit 1
fi

# ── assertion 1: unknown option is rejected before any configuration is read ──
echo "[1/2] dma -Z  (unknown option -> 'invalid argument' + EX_USAGE)"
a1_rc=0
a1_out=$(dma -Z 2>&1) || a1_rc=$?
echo "      rc=$a1_rc   stderr=[${a1_out}]"
if ! printf '%s' "$a1_out" | grep -q "invalid argument"; then
    echo "      ❌ expected 'invalid argument' in stderr"
    fail=1
fi
if ! printf '%s' "$a1_out" | grep -q -- "-Z"; then
    echo "      ❌ expected the offending option '-Z' to be echoed"
    fail=1
fi
if [ "$a1_rc" -eq 0 ]; then
    echo "      ❌ expected a non-zero exit status for an invalid option"
    fail=1
fi

# ── assertion 2: queue-mode conflict is rejected in the same argument stage ──
# `-bp` sets showq (dma.c:513-515) and `-q` sets doqueue (dma.c:555); with no
# operand following `-q`, musl's getopt missing-argument path leaves
# optind == argc+1, so `argc -= optind` (dma.c:585) yields -1 != 0 and the
# operand guard at dma.c:589 fires first:
#   dma.c:590 errx(EX_USAGE, "sending mail and queue operations are mutually exclusive")
# Still upstream of parse_conf at dma.c:606. Observed 2026-10-08 on the
# packaged binary (rc=64); the dma.c:592/593 branch needs an extra operand
# token (e.g. `dma -bp -q x`), which is not this assertion's command.
echo "[2/2] dma -bp -q  (queue-mode conflict rejected -> EX_USAGE)"
a2_rc=0
a2_out=$(dma -bp -q 2>&1) || a2_rc=$?
echo "      rc=$a2_rc   stderr=[${a2_out}]"
if ! printf '%s' "$a2_out" | grep -q "sending mail and queue operations are mutually exclusive"; then
    echo "      ❌ expected 'sending mail and queue operations are mutually exclusive' in stderr"
    fail=1
fi
if [ "$a2_rc" -eq 0 ]; then
    echo "      ❌ expected a non-zero exit status for the queue-mode conflict"
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "❌ dma test_package FAILED"
    exit 1
fi
echo "✅ dma test_package PASSED (2/2 assertions)"
