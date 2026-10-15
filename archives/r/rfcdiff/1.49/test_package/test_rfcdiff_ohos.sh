#!/bin/bash
# test_rfcdiff_ohos.sh — HarmonyOS-specific runtime tests for the packaged rfcdiff.
#
# Covers exactly what patches/0001-rfcdiff.patch
# changes: the OHOS bash shebang (E165) and the $TMPDIR-based work directory
# (E002, /tmp is read-only on HarmonyOS). Each case runs the packaged tool on
# real drafts and checks observable behaviour. A case whose precondition does
# not hold on this host prints SKIP and is never counted as a pass.
# Fixtures are written with printf, never with here-documents (E547).
#
# Usage: test_rfcdiff_ohos.sh <path-to-rfcdiff> <writable-work-dir>
set -u

RFCDIFF="${1:?usage: test_rfcdiff_ohos.sh <path-to-rfcdiff> <work-dir>}"
BASE="${2:?usage: test_rfcdiff_ohos.sh <path-to-rfcdiff> <work-dir>}"
OHOS_BASH=/data/service/hnp/bin/bash

pass=0
fail=0
skip=0
ok() { echo "PASS: $1"; pass=$((pass + 1)); }
no() { echo "FAIL: $1 -- $2"; fail=$((fail + 1)); }
sk() { echo "SKIP: $1 -- $2"; skip=$((skip + 1)); }

WORK="$BASE/rfcdiff-tp-ohos"
rm -rf "$WORK"
mkdir -p "$WORK/tmp" || { echo "FAIL: cannot create $WORK"; exit 1; }
cd "$WORK" || exit 1

printf '%s\n' "Abstract" "" "   The widget frobnicates the old gadget." "" \
    "Author   Expires 1 July 2025   [Page 1]" > draft-ohos-00.txt
printf '%s\n' "Abstract" "" "   The widget frobnicates the new gadget." "" \
    "Author   Expires 1 July 2025   [Page 1]" > draft-ohos-01.txt
for f in draft-ohos-00.txt draft-ohos-01.txt; do
    [ -s "$f" ] || { echo "FAIL: fixture $f is empty"; exit 1; }
done

# ── OHOS-1: packaged shebang is the HarmonyOS bash (E165) ───────────────────
head1=$(head -n 1 "$RFCDIFF")
if [ "$head1" = "#!$OHOS_BASH" ]; then ok "packaged shebang is #!$OHOS_BASH"
else no "packaged shebang is #!$OHOS_BASH" "got '$head1'"; fi

# ── OHOS-2: the shebang interpreter really runs the packaged tool ───────────
# Direct execution is tried first. Conan's cache may sit on HMDFS, where exec
# bits are not honoured; then the shebang interpreter itself must run the
# script, and the PASS line says which path was taken.
if [ -x "$OHOS_BASH" ]; then
    expect=$(printf '%s\n' ' Abstract' ' ' '-   The widget frobnicates the old gadget.' \
        '+   The widget frobnicates the new gadget.')
    out=$("$RFCDIFF" --diff --nowdiff --stdout draft-ohos-00.txt draft-ohos-01.txt 2>/dev/null | tail -n +4)
    path=direct
    if [ "$out" != "$expect" ]; then
        out=$("$OHOS_BASH" "$RFCDIFF" --diff --nowdiff --stdout draft-ohos-00.txt draft-ohos-01.txt 2>/dev/null | tail -n +4)
        path="$OHOS_BASH (direct exec unavailable here)"
    fi
    if [ "$out" = "$expect" ]; then ok "rfcdiff diffs two drafts through the OHOS bash ($path)"
    else no "rfcdiff diffs two drafts through the OHOS bash" "got '$out'"; fi
else
    sk "rfcdiff runs through $OHOS_BASH" "interpreter absent on this host"
fi

# ── OHOS-3: work directory is created under $TMPDIR, not /tmp (E002) ────────
# --keep leaves the work directory behind and packs it next to itself; the
# unpatched script would have created both under /tmp regardless of $TMPDIR.
out=$(TMPDIR="$WORK/tmp" bash "$RFCDIFF" --keep --diff --nowdiff --stdout draft-ohos-00.txt draft-ohos-01.txt 2>&1)
kept=$(printf '%s\n' "$out" | sed -n 's#.*left in \(.*\)/, and packed up in .*#\1#p')
case "$kept" in
    "$WORK/tmp"/rfcdiff-*)
        if [ -d "$kept" ] && [ -f "$kept.tgz" ]; then ok "--keep work directory and tarball live under \$TMPDIR"
        else no "--keep work directory and tarball live under \$TMPDIR" "missing $kept or $kept.tgz"; fi ;;
    *) no "--keep work directory and tarball live under \$TMPDIR" "reported '$kept'" ;;
esac

# ── OHOS-4: a normal run cleans its $TMPDIR work directory up ───────────────
rm -rf "$WORK/tmp2"
mkdir -p "$WORK/tmp2"
TMPDIR="$WORK/tmp2" bash "$RFCDIFF" --chbars --nowdiff --stdout draft-ohos-00.txt draft-ohos-01.txt > chbars.out 2>/dev/null
rc=$?
left=$(ls "$WORK/tmp2" | wc -l)
if [ "$rc" -eq 0 ] && [ "$left" -eq 0 ] && grep -qF '|   The widget frobnicates the new gadget.' chbars.out; then
    ok "run succeeds with a custom \$TMPDIR and leaves nothing behind"
else
    no "run succeeds with a custom \$TMPDIR and leaves nothing behind" "rc=$rc left=$left"
fi

# ── OHOS-5: an unusable $TMPDIR is honoured verbatim (no silent /tmp fallback)
out=$(TMPDIR="$WORK/does-not-exist" bash "$RFCDIFF" --diff --nowdiff --stdout draft-ohos-00.txt draft-ohos-01.txt 2>&1)
rc=$?
if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -q "Failed to create temporary directory '$WORK/does-not-exist/rfcdiff-"; then
    ok "unusable \$TMPDIR fails loudly instead of falling back to /tmp"
else
    no "unusable \$TMPDIR fails loudly instead of falling back to /tmp" "rc=$rc out='$out'"
fi

echo "rfcdiff HarmonyOS tests: pass=$pass fail=$fail skip=$skip"
[ "$fail" -eq 0 ]
