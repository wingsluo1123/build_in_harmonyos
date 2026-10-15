#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer smoke test for the packaged xwax binary.
#
# R34/PF3: this genuinely executes the packaged ELF (not a print-only stub).
# `xwax --help` is the one startup path that exercises locale/encoding setup,
# thread + rig initialisation and the option parser, prints the compiled-in
# VERSION banner to stderr, dumps usage to stdout and exits 0 — all without a
# display, a font file or an audio device.
set -u

BIN="${1:?usage: test.sh <path-to-xwax> <package-dir>}"
PKGDIR="${2:-$(dirname "$(dirname "$BIN")")}"

[ -x "$BIN" ] || { echo "[test] binary missing or not executable: $BIN"; exit 1; }

out="$("$BIN" --help 2>&1)"
rc=$?

if [ "$rc" -ne 0 ]; then
    echo "[test] FAIL: xwax --help exited rc=$rc"
    echo "$out" | head -20
    exit 1
fi
echo "[test] xwax --help rc=0"

if ! echo "$out" | grep -q "xwax 1.10"; then
    echo "[test] FAIL: compiled-in version banner 'xwax 1.10' not found"
    echo "$out" | head -10
    exit 1
fi
echo "[test] version banner OK: $(echo "$out" | grep -o 'xwax 1.10' | head -1)"

if ! echo "$out" | grep -q "Usage: xwax"; then
    echo "[test] FAIL: usage text not printed to stdout"
    echo "$out" | head -10
    exit 1
fi
echo "[test] usage text OK"

if ! echo "$out" | grep -q -- "--dummy"; then
    echo "[test] FAIL: --dummy option not listed in usage"
    exit 1
fi
echo "[test] --dummy option listed"

for helper in "libexec/xwax-scan" "libexec/xwax-import"; do
    if [ ! -f "$PKGDIR/$helper" ]; then
        echo "[test] FAIL: packaged helper script missing: $helper"
        exit 1
    fi
done
echo "[test] helper scripts packaged OK"

echo "[test] PASS: xwax consumer smoke test (5 assertions)"
exit 0
