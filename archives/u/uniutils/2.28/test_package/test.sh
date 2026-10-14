#!/bin/sh
# Consumer checks for installed uniutils binaries.
set -eu

BIN="${UNIUTILS_BIN:?UNIUTILS_BIN is required}"
WORK="${TMPDIR:-/tmp}/uniutils-consumer-test.$$"
rm -rf "$WORK"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

for tool in unidesc uniname unihist ExplicateUTF8 unireverse unifuzz unisurrogate; do
    if [ ! -x "$BIN/$tool" ]; then
        echo "FAIL: missing installed executable $BIN/$tool"
        exit 1
    fi
done
echo "PASS: all expected uniutils executables are installed"

python3 - "$WORK/sample.txt" "$WORK/beta.txt" <<'PY'
import pathlib
import sys
pathlib.Path(sys.argv[1]).write_bytes("A\u03b2\n".encode("utf-8"))
pathlib.Path(sys.argv[2]).write_bytes("\u03b2".encode("utf-8"))
PY

"$BIN/uniname" -a "$WORK/sample.txt" >"$WORK/uniname.log" 2>&1
if ! grep -q "GREEK SMALL LETTER BETA" "$WORK/uniname.log"; then
    echo "FAIL: uniname did not identify the Greek beta character"
    cat "$WORK/uniname.log"
    exit 1
fi
echo "PASS: uniname identified a non-ASCII Unicode character"

"$BIN/unidesc" "$WORK/sample.txt" >"$WORK/unidesc.log" 2>&1
if [ ! -s "$WORK/unidesc.log" ]; then
    echo "FAIL: unidesc produced no output"
    exit 1
fi
echo "PASS: unidesc accepted the UTF-8 input"

"$BIN/unireverse" < "$WORK/sample.txt" >"$WORK/reversed.txt" 2>"$WORK/unireverse.err"
python3 - "$WORK/reversed.txt" "$WORK/unireverse.err" <<'PY'
import pathlib
import sys
actual = pathlib.Path(sys.argv[1]).read_bytes()
expected = "\u03b2A\n".encode("utf-8")
if actual != expected:
    print("FAIL: unireverse returned unexpected bytes", actual, file=sys.stderr)
    print(pathlib.Path(sys.argv[2]).read_text(errors="replace"), file=sys.stderr)
    raise SystemExit(1)
PY
echo "PASS: unireverse reversed UTF-8 characters without data loss"

"$BIN/unihist" -cg < "$WORK/sample.txt" >"$WORK/unihist.log" 2>&1
if ! grep -q '0x0003B2' "$WORK/unihist.log"; then
    echo "FAIL: unihist did not report the expected Unicode code point"
    cat "$WORK/unihist.log"
    exit 1
fi
echo "PASS: unihist emitted the expected code point for UTF-8 input"

"$BIN/ExplicateUTF8" "$WORK/beta.txt" >"$WORK/explicate.log" 2>&1
if ! grep -q 'valid UTF-8 character encoding equivalent to UTF32 0x000003B2' "$WORK/explicate.log"; then
    echo "FAIL: ExplicateUTF8 did not explain the valid UTF-8 character"
    cat "$WORK/explicate.log"
    exit 1
fi
echo "PASS: ExplicateUTF8 explained the valid UTF-8 character"

"$BIN/unifuzz" -q -b -g -S -r 2 -s 123 >"$WORK/unifuzz-1.bin" 2>"$WORK/unifuzz-1.err"
"$BIN/unifuzz" -q -b -g -S -r 2 -s 123 >"$WORK/unifuzz-2.bin" 2>"$WORK/unifuzz-2.err"
if [ ! -s "$WORK/unifuzz-1.bin" ] || ! cmp -s "$WORK/unifuzz-1.bin" "$WORK/unifuzz-2.bin"; then
    echo "FAIL: unifuzz did not produce deterministic output for a fixed seed"
    exit 1
fi
echo "PASS: unifuzz produced deterministic output for a fixed seed"

"$BIN/unisurrogate" 1F600 >"$WORK/unisurrogate.log" 2>&1
if ! grep -q 'U+1F600' "$WORK/unisurrogate.log" || ! grep -q 'U+D83D U+DE00' "$WORK/unisurrogate.log"; then
    echo "FAIL: unisurrogate did not calculate the expected surrogate pair"
    cat "$WORK/unisurrogate.log"
    exit 1
fi
echo "PASS: unisurrogate calculated the expected surrogate pair"
echo "PASS: all uniutils consumer checks passed"
