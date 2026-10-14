#!/bin/sh
# Consumer end-to-end test for loudgain on OHOS.
#
# Workflow: version banner -> help -> generate a noise WAV (pure shell, no
# external fixture) -> loudgain scan+tag write (FFmpeg decode + libebur128
# analysis + TagLib write) -> structural + byte-level tag verification ->
# re-run with tags already present.
#
# 6 assertions, abort on first failure.
#
# Portability note (E265-style OHOS toolchain differences): the system grep
# (/system/bin/toybox) treats files containing NUL bytes as binary and does
# NOT match them even with -a, while GNU grep does.  Byte-level checks on
# binary files therefore strip NULs with `tr -d '\000'` first, which behaves
# identically under toybox/busybox/GNU grep.

set -e

BINDIR="${LOUDGAIN_BINDIR:?LOUDGAIN_BINDIR not set}"
LOUDGAIN="$BINDIR/loudgain"

assert() {
    # assert <description> <command...>
    desc="$1"; shift
    if "$@" >/dev/null 2>&1; then
        echo "PASS: $desc"
    else
        echo "FAIL: $desc" >&2
        exit 1
    fi
}

# --- assertion 1: version banner (binary starts, all shared deps resolve) ---
VER="$("$LOUDGAIN" --version 2>&1)"
echo "$VER" | grep -q "0\.6\.8" || {
    echo "FAIL: version banner does not mention 0.6.8: $VER" >&2
    exit 1
}
echo "PASS: version banner reports 0.6.8"

# --- assertion 2: help output mentions ReplayGain (CLI sanity) ---
assert "help output mentions ReplayGain" sh -c "\"$LOUDGAIN\" --help 2>&1 | grep -qi replaygain"

# --- generate a 1s 8kHz mono 16-bit noise WAV (no silence: urandom) ---
WORK="$(pwd)/loudgain-e2e.$$"
mkdir -p "$WORK"
# shellcheck disable=SC2064
trap 'rm -rf "$WORK" 2>/dev/null || true' EXIT
WAV="$WORK/test-noise.wav"
# 16000 data bytes = 8000 samples; RIFF size = 36 + 16000 = 16036 = 0x3EA4
printf 'RIFF\xa4\x3e\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data\x80\x3e\x00\x00' > "$WORK/header.bin"
dd if=/dev/urandom of="$WORK/noise.bin" bs=16000 count=1 2>/dev/null
cat "$WORK/header.bin" "$WORK/noise.bin" > "$WAV"
SIZE=$(wc -c < "$WAV")
[ "$SIZE" -ge 16044 ] || {
    echo "FAIL: WAV generation produced $SIZE bytes (expected >= 16044)" >&2
    exit 1
}
echo "PASS: generated $SIZE-byte noise WAV"

# --- assertion 3: scan + write tags (decode -> EBU R128 -> report) ---
# No -q: loudgain's report table is captured so a silent tag-write failure
# ("Couldn't write to: ...") becomes visible in the failure message.
OUT="$("$LOUDGAIN" -s i "$WAV" 2>&1)" && RC=0 || RC=$?
if [ "$RC" -ne 0 ]; then
    echo "FAIL: loudgain scan+write exited $RC: $OUT" >&2
    exit 1
fi
case "$OUT" in
    *"Couldn't write"*)
        echo "FAIL: loudgain reported a tag write failure: $OUT" >&2
        exit 1
        ;;
esac
echo "PASS: loudgain scan+write rc=0"

# --- assertion 4: structural — the ID3 chunk physically grew the file ---
SIZE2=$(wc -c < "$WAV")
if [ "$SIZE2" -gt "$SIZE" ]; then
    echo "PASS: tag write grew file by $((SIZE2 - SIZE)) bytes"
else
    echo "FAIL: file size unchanged after tag write ($SIZE -> $SIZE2); loudgain output: $OUT" >&2
    exit 1
fi

# --- assertion 5: ReplayGain frames physically written into the WAV ---
# Toybox grep skips NUL-containing (binary) files even with -a; strip NULs
# first so the check is identical under toybox/busybox/GNU grep.
if tr -d '\000' < "$WAV" | grep -q "REPLAYGAIN_TRACK_GAIN"; then
    echo "PASS: REPLAYGAIN_TRACK_GAIN frame present in WAV"
else
    echo "FAIL: REPLAYGAIN_TRACK_GAIN frame present in WAV (size $SIZE2); loudgain output: $OUT" >&2
    exit 1
fi

# --- assertion 6: re-run with tags already present (tag re-read path) ---
"$LOUDGAIN" -s i -q "$WAV" >/dev/null 2>&1 || {
    echo "FAIL: second loudgain run (tags present) failed" >&2
    exit 1
}
echo "PASS: second run with pre-existing tags rc=0"

echo "ALL 6 ASSERTIONS PASSED"
