#!/bin/sh
# Consumer checks for the installed jitterdebugger binaries.
set -eu

BIN="${JITTERDEBUGGER_BIN:?JITTERDEBUGGER_BIN is required}"
WORK="${TMPDIR:-/tmp}/jitterdebugger-consumer-test.$$"
rm -rf "$WORK"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

for tool in jitterdebugger jittersamples jitterplot; do
    if [ ! -f "$BIN/$tool" ]; then
        echo "FAIL: missing installed file $BIN/$tool"
        exit 1
    fi
done
echo "PASS: jitterdebugger tool files are installed"

for tool in jitterdebugger jittersamples jitterplot; do
    if [ ! -x "$BIN/$tool" ]; then
        echo "FAIL: installed tool is not executable: $BIN/$tool"
        exit 1
    fi
done
echo "PASS: all jitterdebugger tools are executable"

"$BIN/jitterdebugger" --version >"$WORK/jd.version" 2>&1
if ! grep -qx 'jitterdebugger 0.3' "$WORK/jd.version"; then
    echo "FAIL: jitterdebugger --version did not report version 0.3"
    cat "$WORK/jd.version"
    exit 1
fi
echo "PASS: jitterdebugger --version works"

"$BIN/jitterdebugger" -h >"$WORK/jd.help" 2>&1
if ! grep -q 'General usage:' "$WORK/jd.help"; then
    echo "FAIL: jitterdebugger -h did not print help"
    cat "$WORK/jd.help"
    exit 1
fi
echo "PASS: jitterdebugger -h prints help"

"$BIN/jittersamples" --version >"$WORK/js.version" 2>&1
if ! grep -qx 'jittersamples 0.3' "$WORK/js.version"; then
    echo "FAIL: jittersamples --version did not report version 0.3"
    cat "$WORK/js.version"
    exit 1
fi
echo "PASS: jittersamples --version works"

"$BIN/jittersamples" -h >"$WORK/js.help" 2>&1
if ! grep -q 'jittersamples \[options\] \[DIR\]' "$WORK/js.help"; then
    echo "FAIL: jittersamples -h did not print help"
    cat "$WORK/js.help"
    exit 1
fi
echo "PASS: jittersamples -h prints help"

if ! head -n 1 "$BIN/jitterplot" | grep -q '^#!.*python'; then
    echo "FAIL: jitterplot does not have a Python shebang"
    exit 1
fi
echo "PASS: jitterplot has a Python shebang"

python3 - "$WORK" <<'PY'
import pathlib
import struct
import sys
work = pathlib.Path(sys.argv[1])
(work / "cpus_online").write_text("1\n", encoding="ascii")
# struct latency_sample: uint32_t cpuid; struct timespec ts; uint64_t val
record = struct.pack("<IqqQ", 0, 1, 500000000, 42)
(work / "samples.raw").write_bytes(record)
PY

"$BIN/jittersamples" -f csv "$WORK" >"$WORK/decode.log" 2>&1
if [ ! -s "$WORK/samples.csv" ]; then
    echo "FAIL: jittersamples did not create samples.csv"
    cat "$WORK/decode.log"
    exit 1
fi
if [ "$(wc -l < "$WORK/samples.csv" | tr -d ' ')" != "1" ] || ! grep -qx '0;1.500000000;42' "$WORK/samples.csv"; then
    echo "FAIL: samples.csv contents are unexpected"
    cat "$WORK/samples.csv"
    exit 1
fi
echo "PASS: jittersamples decoded a real upstream sample record to CSV"
echo "PASS: all jitterdebugger consumer checks passed"
