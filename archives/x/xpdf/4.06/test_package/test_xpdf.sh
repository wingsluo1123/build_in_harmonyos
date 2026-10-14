#!/bin/sh
# xpdf 4.06 consumer test — runs the INSTALLED CLI artifacts and asserts on real side
# effects (file content, produced bytes, extracted text), never on exit codes alone.
#
# Why not exit codes: a short flag like `-v` can swallow its argument and still exit 0
# without doing anything, and tools can "succeed" vacuously. Verified on a real 4.06
# build: `pdfimages -png x.pdf out` prints usage and exits 99, and `pdfimages x.pdf out`
# on an image-less page exits 0 while writing **no file at all**. Every assertion below
# therefore checks a produced artifact on disk.
#
# NOTE: deliberately no `set -e` — several checks below *expect* a command to fail
# (negative controls, truncated input). `set -e` would abort the run on the first
# such command and silently skip the remaining assertions.
set -u

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
WORK="${TMPDIR:-.}/xpdf-test-work.$$"
rm -rf "$WORK"
mkdir -p "$WORK" || exit 1
trap 'rm -rf "$WORK"' EXIT

fail=0
pass=0
ok()  { pass=$((pass + 1)); echo "PASS: $1"; }
bad() { fail=$((fail + 1)); echo "FAIL: $1"; }

find_tool() { command -v "$1" 2>/dev/null || true; }

PDFTOTEXT=$(find_tool pdftotext)
PDFINFO=$(find_tool pdfinfo)
PDFFONTS=$(find_tool pdffonts)
PDFIMAGES=$(find_tool pdfimages)
PDFDETACH=$(find_tool pdfdetach)

if [ -z "$PDFTOTEXT" ]; then
    echo "FATAL: pdftotext not on PATH; the package did not install its CLI tools" >&2
    exit 1
fi
echo "using pdftotext=$PDFTOTEXT"

# ---------------------------------------------------------------- fixture
# The generator prints one value per line: the text encoded on the page, the embedded
# file's name, and the embedded file's payload. The shell asserts against those
# instead of a second hardcoded copy of each string that could drift apart.
META=$(python3 "$HERE/gen_fixture.py" "$WORK/sample.pdf")
EXPECTED=$(printf '%s\n' "$META" | sed -n 1p)
ATTACH_NAME=$(printf '%s\n' "$META" | sed -n 2p)
ATTACH_PAYLOAD=$(printf '%s\n' "$META" | sed -n 3p)
if [ -s "$WORK/sample.pdf" ] && [ -n "$EXPECTED" ] && [ -n "$ATTACH_NAME" ] \
        && [ -n "$ATTACH_PAYLOAD" ]; then
    ok "fixture generated non-empty ($WORK/sample.pdf)"
else
    bad "fixture generated non-empty ($WORK/sample.pdf)"
    echo "cannot continue without a fixture" >&2
    exit 1
fi

# ------------------------------------------------------- 1. version banner
VOUT=$($PDFTOTEXT -v 2>&1 || true)
if echo "$VOUT" | grep -q "xpdf"; then
    ok "pdftotext -v reports an xpdf version string"
else
    bad "pdftotext -v reports an xpdf version string (got: $VOUT)"
fi

# ------------------------------------- 2. real text extraction (the core)
# Functional roundtrip: a PDF in, the expected words out.
$PDFTOTEXT "$WORK/sample.pdf" "$WORK/out.txt" 2>"$WORK/err.txt" || true
if [ -s "$WORK/out.txt" ]; then
    ok "pdftotext produced a non-empty .txt for the fixture"
else
    bad "pdftotext produced a non-empty .txt for the fixture"
fi
if grep -q "$EXPECTED" "$WORK/out.txt" 2>/dev/null; then
    ok "extracted text contains '$EXPECTED'"
else
    bad "extracted text contains '$EXPECTED' (got: $(cat "$WORK/out.txt" 2>/dev/null | tr '\n' ' '))"
fi
# Negative control: a sentinel that is NOT in the PDF must not appear.
if grep -q "NOT-IN-THE-PDF-9f3a" "$WORK/out.txt" 2>/dev/null; then
    bad "extracted text does not contain an absent sentinel"
else
    ok "extracted text does not contain an absent sentinel"
fi

# --------------------------- 3. layout metadata reflects the real page
$PDFINFO "$WORK/sample.pdf" >"$WORK/info.txt" 2>/dev/null || true
if grep -qi "^Pages:[[:space:]]*1" "$WORK/info.txt" 2>/dev/null; then
    ok "pdfinfo reports Pages: 1 for the single-page fixture"
else
    bad "pdfinfo reports Pages: 1 (got: $(tr '\n' '|' < "$WORK/info.txt" 2>/dev/null))"
fi
if grep -qi "612 x 792" "$WORK/info.txt" 2>/dev/null; then
    ok "pdfinfo reports the fixture MediaBox 612 x 792"
else
    bad "pdfinfo reports MediaBox 612 x 792"
fi

# ------------------- 4. font enumeration finds the one declared font
$PDFFONTS "$WORK/sample.pdf" >"$WORK/fonts.txt" 2>/dev/null || true
if grep -q "Helvetica" "$WORK/fonts.txt" 2>/dev/null; then
    ok "pdffonts lists the Helvetica resource declared by the fixture"
else
    bad "pdffonts lists the Helvetica resource declared by the fixture"
fi

# ------------------- 5. pdfimages extracts the embedded image as real bytes
# NOTE: xpdf's pdfimages has NO -png option (prints usage, exits 99 — verified on a real
# 4.06 build); it writes PPM by default. Use the default form. The fixture embeds a
# 2x2 DeviceRGB image because an image-less page produces no output file at all.
$PDFIMAGES "$WORK/sample.pdf" "$WORK/img" 2>/dev/null || true
if ls "$WORK"/img*.ppm >/dev/null 2>&1 || ls "$WORK"/img*.pgm >/dev/null 2>&1; then
    ok "pdfimages wrote an image file for the embedded XObject"
else
    bad "pdfimages wrote an image file for the embedded XObject"
fi
# Assert decoded content, not just "a file appeared": PPM header, the declared 2x2
# dimensions, and a non-empty pixel payload.
if ls "$WORK"/img*.ppm >/dev/null 2>&1; then
    IMG=$(ls "$WORK"/img*.ppm | head -1)
    if head -3 "$IMG" | grep -q "^P6"; then
        ok "extracted image has a binary PPM (P6) header"
    else
        bad "extracted image has a binary PPM (P6) header"
    fi
    if head -2 "$IMG" | tail -1 | grep -qE "^2[[:space:]]+2$"; then
        ok "extracted image dimensions are the declared 2x2"
    else
        bad "extracted image dimensions are the declared 2x2 (got: $(head -2 "$IMG" | tail -1))"
    fi
    if [ "$(wc -c < "$IMG")" -gt 16 ]; then
        ok "extracted image carries a non-empty pixel payload"
    else
        bad "extracted image carries a non-empty pixel payload"
    fi
fi
# -listonly is the form that needs no output root (verified on a real build).
if $PDFIMAGES -listonly "$WORK/sample.pdf" 2>/dev/null | grep -q "colorspace=DeviceRGB"; then
    ok "pdfimages -listonly reports the DeviceRGB image it found"
else
    bad "pdfimages -listonly reports the DeviceRGB image it found"
fi

# ------------------- 6. pdfdetach lists the attachment and really detaches it
# Content assertions, never `-f` on a redirect target: the shell creates/truncates the
# redirect file BEFORE the command runs, so `-f` passes even when the tool is missing,
# crashes, or prints nothing (AI review f43c32aa — the previous `-f "$WORK/detach.txt"`
# form was vacuously true). stdout is separated from stderr so an error message can
# never be mistaken for a report. Upstream prints "<n> embedded files" and then one
# "N: <name>" line per attachment (pdfdetach.cc:146-148), which is what is keyed on.
$PDFDETACH -list "$WORK/sample.pdf" >"$WORK/detach.txt" 2>"$WORK/detach.err" || true
if [ -n "$PDFDETACH" ] && [ -s "$WORK/detach.txt" ]; then
    ok "pdfdetach -list produced a non-empty report"
else
    bad "pdfdetach -list produced a non-empty report (pdfdetach='${PDFDETACH}', stderr: $(tr '\n' ' ' < "$WORK/detach.err" 2>/dev/null))"
fi
if grep -q "^1 embedded files$" "$WORK/detach.txt" 2>/dev/null \
        && grep -qF "$ATTACH_NAME" "$WORK/detach.txt" 2>/dev/null; then
    ok "pdfdetach -list counts the attachment and prints its name"
else
    bad "pdfdetach -list counts the attachment and prints its name (got: $(tr '\n' '|' < "$WORK/detach.txt" 2>/dev/null))"
fi
$PDFDETACH -save 1 -o "$WORK/extracted.txt" "$WORK/sample.pdf" >/dev/null 2>"$WORK/detach-save.err" || true
if [ -n "$PDFDETACH" ] && grep -qF "$ATTACH_PAYLOAD" "$WORK/extracted.txt" 2>/dev/null; then
    ok "pdfdetach -save writes the embedded payload byte-for-byte"
else
    bad "pdfdetach -save writes the embedded payload byte-for-byte (stderr: $(tr '\n' ' ' < "$WORK/detach-save.err" 2>/dev/null))"
fi

# ------------------- 7. error path is distinguishable from success
# A truncated file must not yield a clean extraction of the real text. A build whose
# parser is not actually parsing would pass here.
head -c 200 "$WORK/sample.pdf" >"$WORK/truncated.pdf"
$PDFTOTEXT "$WORK/truncated.pdf" "$WORK/trunc.txt" >/dev/null 2>&1
TRUNC_RC=$?
echo "  truncated-input exit code: $TRUNC_RC"
if [ "$TRUNC_RC" -eq 0 ]; then
    # Tolerated only if nothing was fabricated.
    if [ ! -s "$WORK/trunc.txt" ] || ! grep -q "$EXPECTED" "$WORK/trunc.txt" 2>/dev/null; then
        ok "truncated input yields no fabricated text"
    else
        bad "truncated input yielded the real text (parser not actually parsing?)"
    fi
else
    ok "truncated input reported failure (rc=$TRUNC_RC)"
fi

echo "----------------------------------------"
echo "passed: $pass   failed: $fail"
if [ "$fail" -ne 0 ]; then
    echo "XPDF CLI CONSUMER TESTS FAILED"
    exit 1
fi
echo "ALL XPDF CLI CONSUMER TESTS PASSED"
