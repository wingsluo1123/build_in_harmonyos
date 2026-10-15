#!/bin/bash
# test_rfcdiff.sh — functional tests that drive the packaged rfcdiff tool.
#
# Two synthetic Internet-Drafts (with page headers/footers and a form feed) are
# written with printf, rfcdiff from the Conan package diffs them in every output
# mode and the produced bytes are compared with the expected result. Fixtures
# never use here-documents: /system/bin/sh on the device backs them with a file
# under the read-only /tmp and silently leaves an empty file (knowledge E547).
#
# Usage: test_rfcdiff.sh <path-to-rfcdiff> <writable-work-dir>
set -u

RFCDIFF="${1:?usage: test_rfcdiff.sh <path-to-rfcdiff> <work-dir>}"
BASE="${2:?usage: test_rfcdiff.sh <path-to-rfcdiff> <work-dir>}"

pass=0
fail=0
ok() { echo "PASS: $1"; pass=$((pass + 1)); }
no() { echo "FAIL: $1 -- $2"; fail=$((fail + 1)); }

WORK="$BASE/rfcdiff-tp-generic"
rm -rf "$WORK"
mkdir -p "$WORK/tmp" || { echo "FAIL: cannot create $WORK"; exit 1; }
cd "$WORK" || exit 1
export TMPDIR="$WORK/tmp"

# mkdraft <file> <draft-name> <body line>...
mkdraft() {
    local f="$1" name="$2"
    shift 2
    {
        printf '%s\n' \
            "Network Working Group                                         A. Author" \
            "Internet-Draft                                              Example Org" \
            "Intended status: Informational                           1 January 2025" \
            "" \
            "" \
            "                        Sample Protocol Spec" \
            "                        $name" \
            "" \
            "Abstract" \
            ""
        local l
        for l in "$@"; do printf '   %s\n' "$l"; done
        printf '%s\n' \
            "" \
            "" \
            "Author                  Expires 1 July 2025                    [Page 1]"
        printf '\f\n'
        printf '%s\n' \
            "Internet-Draft           Sample Spec                  January 2025" \
            "" \
            "1.  Introduction" \
            "" \
            "   This document describes a widget protocol." \
            "" \
            "Author                  Expires 1 July 2025                    [Page 2]"
    } > "$f"
}

mkdraft draft-sample-00.txt draft-sample-00 \
    "The widget frobnicates the old gadget." "Second line stays the same."
mkdraft draft-sample-01.txt draft-sample-01 \
    "The widget frobnicates the new gadget quickly." "Second line stays the same." \
    "Added a third line."
for f in draft-sample-00.txt draft-sample-01.txt; do
    [ -s "$f" ] || { echo "FAIL: fixture $f is empty"; exit 1; }
done

# ── 1. --version ────────────────────────────────────────────────────────────
out=$(bash "$RFCDIFF" --version 2>&1 | head -n 1 | tr -d '\t ')
if [ "$out" = "rfcdiff1.49" ]; then ok "--version reports rfcdiff 1.49"
else no "--version reports rfcdiff 1.49" "got '$out'"; fi

# ── 2. --diff: headers/footers stripped, change hunks exact ─────────────────
printf '%s\n' \
    " Network Working Group                                         A. Author" \
    " Internet-Draft                                              Example Org" \
    " Intended status: Informational                           1 January 2025" \
    " " \
    "                         Sample Protocol Spec" \
    "-                        draft-sample-00" \
    "+                        draft-sample-01" \
    " " \
    " Abstract" \
    " " \
    "-   The widget frobnicates the old gadget." \
    "+   The widget frobnicates the new gadget quickly." \
    "    Second line stays the same." \
    "+   Added a third line." \
    " " \
    " 1.  Introduction" \
    " " \
    "    This document describes a widget protocol." > exp.diff.body
bash "$RFCDIFF" --diff --nowdiff --stdout draft-sample-00.txt draft-sample-01.txt > got.diff 2>/dev/null
rc=$?
# first two lines carry file mtimes; the hunk header "@@ -1,15 +1,16 @@" is kept
sed -e '1,3d' got.diff > got.diff.body
if [ "$rc" -eq 0 ] && cmp -s exp.diff.body got.diff.body; then
    ok "--diff output is exact (page header/footer stripped)"
else
    no "--diff output is exact" "rc=$rc"; diff exp.diff.body got.diff.body | head -n 20
fi
if grep -q '^@@ -1,15 +1,16 @@' got.diff; then ok "--diff hunk header matches stripped line counts"
else no "--diff hunk header matches stripped line counts" "$(sed -n 3p got.diff)"; fi

# ── 3. --chbars: changebar marks the added/changed lines only ───────────────
bash "$RFCDIFF" --chbars --nowdiff --stdout draft-sample-00.txt draft-sample-01.txt > got.chbars 2>/dev/null
rc=$?
marked=$(grep -c '^|' got.chbars)
if [ "$rc" -eq 0 ] && [ "$marked" -eq 3 ] \
    && grep -qF '|   Added a third line.' got.chbars \
    && grep -qF '|                        draft-sample-01' got.chbars \
    && grep -qF '|   The widget frobnicates the new gadget quickly.' got.chbars \
    && ! grep -q 'draft-sample-00' got.chbars; then
    ok "--chbars marks exactly the 3 changed lines"
else
    no "--chbars marks exactly the 3 changed lines" "rc=$rc marked=$marked"
fi

# ── 4. --html (default mode): side-by-side table with insert/delete spans ───
bash "$RFCDIFF" --html --nowdiff --stdout draft-sample-00.txt draft-sample-01.txt > got.html 2>/dev/null
rc=$?
if [ "$rc" -eq 0 ] && grep -q '<html' got.html \
    && grep -qF '<span class="delete">old gadget</span>' got.html \
    && grep -qF '<span class="insert">new gadget quickly</span>' got.html \
    && grep -qF 'Added a third line.' got.html; then
    ok "--html marks word-level insertions and deletions"
else
    no "--html marks word-level insertions and deletions" "rc=$rc"
fi
if ! grep -q 'Page [12]\]' got.html; then ok "--html output has no page footers"
else no "--html output has no page footers" "footer leaked into html"; fi

# ── 5. --nostrip keeps page headers/footers ─────────────────────────────────
bash "$RFCDIFF" --diff --nowdiff --nostrip --stdout draft-sample-00.txt draft-sample-01.txt > got.nostrip 2>/dev/null
if grep -q '\[Page 1\]' got.nostrip; then ok "--nostrip keeps page footers (strip is real)"
else no "--nostrip keeps page footers" "footer missing"; fi

# ── 6. default output file name and --stdout-less run ───────────────────────
rm -f ./*.chbar ./*.diff 2>/dev/null
bash "$RFCDIFF" --chbars --nowdiff draft-sample-00.txt draft-sample-01.txt > /dev/null 2>&1
if [ -s draft-sample-01-from-0.chbar ]; then ok "default output file draft-sample-01-from-0.chbar written"
else no "default output file written" "$(ls)"; fi

# ── 7. identical inputs and usage error ─────────────────────────────────────
out=$(bash "$RFCDIFF" draft-sample-00.txt draft-sample-00.txt 2>&1)
if [ "$out" = "The files are the same file" ]; then ok "same file is detected"
else no "same file is detected" "got '$out'"; fi
bash "$RFCDIFF" > usage.out 2>&1
rc=$?
if [ "$rc" -eq 1 ] && grep -q 'rfcdiff \[options\] file1 file2' usage.out; then ok "missing arguments print usage and exit 1"
else no "missing arguments print usage and exit 1" "rc=$rc"; fi

echo "rfcdiff generic tests: pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
