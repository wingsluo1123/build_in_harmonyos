#!/data/service/hnp/bin/bash
# gem5 test_package — end-to-end SE smoke test of the packaged gem5.opt.
#
# 1. discover the CPython prefix on this worker (PYTHONHOME + libpython for
#    the simulator's embedded interpreter; no device path is hardcoded),
# 2. compile the freestanding AArch64 guest from hello.c with the platform
#    clang,
# 3. run the packaged gem5.opt on that guest in SE mode and assert:
#      a) the simulator exits with status 0,
#      b) its output contains the guest's "Hello world!",
#      c) no "Simulated exit code not 0" is reported,
#      d) a stats.txt was produced.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE="${TMPDIR:-$HOME/tmp}"
if ! mkdir -p "$BASE" 2>/dev/null || [ ! -w "$BASE" ]; then
    BASE="$HOME/tmp"
    mkdir -p "$BASE"
fi
WORK="$(mktemp -d "$BASE/gem5-test-XXXXXX")"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

echo "[test] workdir: $WORK"

# ── 1. runtime environment for the embedded CPython ──────────────────
PYBIN="${GEM5_TEST_PYTHON:-}"
if [ -z "$PYBIN" ]; then
    PYBIN="$(command -v python3 || true)"
fi
if [ -z "$PYBIN" ] || [ ! -x "$PYBIN" ]; then
    for candidate in \
        "$HOME/.local/bin/python3" \
        /usr/bin/python3 \
        /data/service/hnp/python.org/python_3.12/bin/python3; do
        if [ -x "$candidate" ]; then
            PYBIN="$candidate"
            break
        fi
    done
fi
if [ -z "$PYBIN" ] || [ ! -x "$PYBIN" ]; then
    echo "FAIL: no python3 interpreter found for PYTHONHOME discovery"
    exit 1
fi
PYPREFIX="$("$PYBIN" -c 'import sys; print(sys.base_prefix)')"
export PYTHONHOME="$PYPREFIX"
export LD_LIBRARY_PATH="$PYPREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
echo "[test] PYTHONHOME=$PYTHONHOME"

# ── 2. compile the freestanding AArch64 guest ────────────────────────
CLANG="${GEM5_TEST_CC:-}"
if [ -z "$CLANG" ]; then
    CLANG="$(command -v clang || true)"
fi
if [ -z "$CLANG" ] || [ ! -x "$CLANG" ]; then
    for candidate in /data/service/hnp/bin/clang /usr/bin/clang; do
        if [ -x "$candidate" ]; then
            CLANG="$candidate"
            break
        fi
    done
fi
if [ -z "$CLANG" ] || [ ! -x "$CLANG" ]; then
    echo "FAIL: no clang available to build the guest"
    exit 1
fi
READELF="${GEM5_TEST_READELF:-}"
if [ -z "$READELF" ]; then
    READELF="$(command -v readelf || true)"
fi
if [ -z "$READELF" ] || [ ! -x "$READELF" ]; then
    for candidate in /data/service/hnp/bin/readelf /usr/bin/readelf /bin/readelf; do
        if [ -x "$candidate" ]; then
            READELF="$candidate"
            break
        fi
    done
fi
if [ -z "$READELF" ] || [ ! -x "$READELF" ]; then
    echo "FAIL: no readelf available to inspect the guest"
    exit 1
fi
echo "[test] compiling guest with $CLANG"
"$CLANG" -static -nostdlib -fno-stack-protector -Wl,--build-id=none \
    -O1 -o "$WORK/hello" "$HERE/hello.c"
"$READELF" -h "$WORK/hello" | grep -q "AArch64" || {
    echo "FAIL: guest is not an AArch64 ELF"
    exit 1
}

# ── 3. run the packaged gem5.opt ─────────────────────────────────────
GEM5="$(command -v gem5.opt || true)"
if [ -z "$GEM5" ]; then
    echo "FAIL: gem5.opt not found in PATH (VirtualRunEnv)"
    exit 1
fi
echo "[test] running: $GEM5 -d $WORK/m5out se_hello.py hello"

set +e
"$GEM5" -d "$WORK/m5out" "$HERE/se_hello.py" "$WORK/hello" \
    >"$WORK/gem5.out" 2>"$WORK/gem5.err"
GEM5_RC=$?
set -e

if [ "$GEM5_RC" -ne 0 ]; then
    echo "FAIL: gem5.opt exited with status $GEM5_RC"
    tail -30 "$WORK/gem5.out" "$WORK/gem5.err" || true
    exit 1
fi
echo "[test] assertion 1/4 OK: gem5.opt exit status 0"

if ! grep -q "Hello world!" "$WORK/gem5.out"; then
    echo "FAIL: guest output 'Hello world!' not found"
    tail -30 "$WORK/gem5.out" "$WORK/gem5.err" || true
    exit 1
fi
echo "[test] assertion 2/4 OK: guest printed 'Hello world!'"

if grep -q "Simulated exit code not 0" "$WORK/gem5.out"; then
    echo "FAIL: gem5 reported a non-zero simulated guest exit code"
    grep -n "Simulated exit code" "$WORK/gem5.out" || true
    exit 1
fi
echo "[test] assertion 3/4 OK: no 'Simulated exit code not 0'"

if [ ! -s "$WORK/m5out/stats.txt" ]; then
    echo "FAIL: m5out/stats.txt is missing or empty"
    ls -la "$WORK/m5out" || true
    exit 1
fi
echo "[test] assertion 4/4 OK: m5out/stats.txt produced"

grep -E "Exiting @ tick" "$WORK/gem5.out" || true
echo "PASS: packaged gem5.opt ran an AArch64 SE workload end-to-end"
