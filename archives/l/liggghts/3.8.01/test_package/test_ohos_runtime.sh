#!/usr/bin/env bash
# HarmonyOS-specific RUNTIME behaviour tests for liggghts (companion to
# check_ohos.py, which asserts properties of the artifact itself).
#
# These actually EXECUTE the packaged engine on the target and assert on what it
# reports, so they cover platform behaviour rather than metadata:
#
#   T1  gzip-compressed data file.  LIGGGHTS' -DLAMMPS_GZIP support is
#       implemented with popen("gunzip -c <file>") (src/read_data.cpp), i.e. it
#       needs the external gunzip at RUNTIME - not zlib.  Passing proves both the
#       compiled-in gzip support and that the OHOS image provides the helper.
#   T2  insert/pack driven with "-screen none" (screen == NULL).  This is the
#       runtime regression for patch 0004: upstream Region::reset_random()
#       wrote to `screen` without a NULL check, so the unpatched engine aborts
#       (rc=134, no output at all) on this deck while the patched one finishes -
#       verified by rebuilding with the patch reverted.  Without this test the
#       patch would have no automated coverage.
#   T3  two MPI ranks.  The package IS the MPI build (bin/lmp_mpi), so the
#       parallel path has to work on the target, not just the single-rank one.
#
# Only bash builtins + the packaged tools are used.  Env: run via test_package
# with VirtualRunEnv, so the package bin/ (lmp_mpi) and mpich (mpiexec) are on
# PATH and the runtime library paths are set.

set -euo pipefail

ENGINE="${LIGGGHTS_ENGINE:-lmp_mpi}"
EXPECTED_ATOMS="${LIGGGHTS_EXPECTED_ATOMS:-125}"
FINAL_STEP="${LIGGGHTS_FINAL_STEP:-1000}"
MPIRUN="${LIGGGHTS_MPIEXEC:-mpiexec}"
TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$TEST_DIR"

fails=0
checks=0
note() { printf '[ohos] %s\n' "$1"; }
ok()   { checks=$((checks + 1)); printf '[pass] %s\n' "$1"; }
bad()  { checks=$((checks + 1)); fails=$((fails + 1)); printf '[fail] %s\n' "$1"; }

assert_run() {   # <label> <logfile> <extra-grep-pattern-or-empty>
    local label="$1" log="$2" pat="${3:-}"
    if [ -s "$log" ] && grep -Fq "Loop time of" "$log" \
       && ! grep -Eq '^(ERROR|\*\*\* ERROR)' "$log"; then
        if [ -n "$pat" ] && ! grep -Fq "$pat" "$log"; then
            bad "$label (missing '$pat')"
        else
            ok "$label"
        fi
    else
        bad "$label (no completion banner / reported ERROR)"
        tail -n 10 "$log" || true
    fi
}

command -v "$ENGINE" >/dev/null 2>&1 || { echo "[fail] $ENGINE not on PATH"; exit 1; }
note "engine: $(command -v "$ENGINE")"

# ── T1: gzip-compressed data file (LAMMPS_GZIP -> popen(gunzip)) ─────────────
# Runs the same deck twice - once with the plain data file, once with a gzipped
# copy - and asserts the final thermo rows are IDENTICAL.  That proves the gz
# path yields the same physics (not merely that it starts), and is also how the
# expectation is kept out of the script: the plain run is the reference.
final_row() { grep -E "^[[:space:]]*${FINAL_STEP}[[:space:]]" "$1" | tail -n 1; }

if command -v gunzip >/dev/null 2>&1; then
    rm -f t1-plain.in t1-plain.log t1-gzdata.data.gz t1-gzdata.in t1-gzdata.log
    python3 - <<'PY'
import gzip, shutil
with open("test_liggghts.data", "rb") as src, gzip.open("t1-gzdata.data.gz", "wb") as dst:
    shutil.copyfileobj(src, dst)
deck = open("test_liggghts.in", encoding="utf-8").read()
open("t1-plain.in", "w", encoding="utf-8").write(deck)
open("t1-gzdata.in", "w", encoding="utf-8").write(
    deck.replace("read_data       test_liggghts.data",
                 "read_data       t1-gzdata.data.gz"))
PY
    ok_plain=0; ok_gz=0
    "$ENGINE" -in t1-plain.in  -log t1-plain.log  -screen none >/dev/null 2>&1 && ok_plain=1
    "$ENGINE" -in t1-gzdata.in -log t1-gzdata.log -screen none >/dev/null 2>&1 && ok_gz=1
    if [ "$ok_plain" -eq 1 ] && [ "$ok_gz" -eq 1 ]; then
        assert_run "T1a plain data file runs" t1-plain.log
        assert_run "T1b gzip-compressed data file runs" t1-gzdata.log
        plain_row="$(final_row t1-plain.log || true)"
        gz_row="$(final_row t1-gzdata.log || true)"
        if [ -n "$plain_row" ] && [ "$gz_row" = "$plain_row" ]; then
            ok "T1c gz run reproduces the plain run exactly ($(echo "$plain_row" | awk '{print "step=" $1, "atoms=" $2, "ke=" $3}'))"
        else
            bad "T1c gz run differs from the plain run"
            printf '  plain: %s\n  gz   : %s\n' "$plain_row" "$gz_row"
        fi
    else
        bad "T1 gzip-compressed data file runs (plain=$ok_plain gz=$ok_gz)"
        tail -n 10 t1-gzdata.log 2>/dev/null || true
    fi
    rm -f t1-plain.in t1-plain.log t1-gzdata.data.gz t1-gzdata.in t1-gzdata.log
else
    note "T1 skipped: no gunzip on PATH (LAMMPS_GZIP needs it at runtime)"
fi

# ── T2: insert/pack under -screen none (patch 0004 regression) ───────────────
rm -f t2-insert.log
if "$ENGINE" -in test_ohos_insert_none.in -log t2-insert.log -screen none \
        >/dev/null 2>&1; then
    assert_run "T2 insert/pack with -screen none (patch 0004)" t2-insert.log
else
    bad "T2 insert/pack with -screen none (patch 0004) - engine returned non-zero"
    tail -n 10 t2-insert.log 2>/dev/null || true
fi
rm -f t2-insert.log

# ── T3: two MPI ranks (the package is the MPI build) ────────────────────────
if command -v "$MPIRUN" >/dev/null 2>&1; then
    rm -f t3-2rank.log
    if "$MPIRUN" -n 2 "$(command -v "$ENGINE")" -in test_liggghts.in \
            -log t3-2rank.log -screen none >/dev/null 2>&1; then
        assert_run "T3 runs on 2 MPI ranks" t3-2rank.log "on 2 procs"
    else
        bad "T3 runs on 2 MPI ranks (mpiexec returned non-zero)"
        tail -n 10 t3-2rank.log 2>/dev/null || true
    fi
    rm -f t3-2rank.log
else
    note "T3 skipped: no $MPIRUN on PATH"
fi

echo "[ohos] runtime behaviour: $((checks - fails))/$checks checks passed"
if [ "$fails" -ne 0 ]; then
    echo "[fail] $fails HarmonyOS runtime check(s) failed"
    exit 1
fi
echo "[pass] HarmonyOS runtime behaviour checks passed"
