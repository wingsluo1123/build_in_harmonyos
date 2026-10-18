#!/bin/bash
# test_wit.sh — consumer tests for wit 3.01a (wit / wwt / wdf)
# Runs against the installed package: PATH must contain the package bin dir
# (provided by the VirtualRunEnv 'conanrun' environment).
# Only portable shell tools are used (dd, printf, head, od, tr, grep,
# sha256sum, mktemp); fixtures are crafted by hand, no helper files needed.

set -u

pass=0
fail=0

ok()  { echo "[PASS] $*"; pass=$((pass+1)); }
bad() { echo "[FAIL] $*"; fail=$((fail+1)); }

WIT="$(command -v wit 2>/dev/null || true)"
WWT="$(command -v wwt 2>/dev/null || true)"
WDF="$(command -v wdf 2>/dev/null || true)"

[ -n "$WIT" ] && ok "found wit: $WIT" || bad "wit not found in PATH"
[ -n "$WWT" ] && ok "found wwt: $WWT" || bad "wwt not found in PATH"
[ -n "$WDF" ] && ok "found wdf: $WDF" || bad "wdf not found in PATH"

if [ -z "$WIT" ] || [ -z "$WWT" ] || [ -z "$WDF" ]; then
    echo
    echo "passed: $pass  failed: $fail"
    echo "$fail TEST(S) FAILED (missing binaries)"
    exit 1
fi

elf_ok() {
    local h
    h="$(head -c 20 "$1" | od -An -tx1 | tr -d ' \n')" || return 1
    [ "${#h}" -ge 40 ] || return 1
    [ "${h:0:8}" = "7f454c46" ] || return 1
    [ "${h:8:2}" = "02" ] || return 1
    [ "${h:10:2}" = "01" ] || return 1
    [ "${h:32:4}" = "0300" ] || return 1
    [ "${h:36:4}" = "b700" ] || return 1
}

for b in wit wwt wdf; do
    p="$(command -v "$b" 2>/dev/null || true)"
    if [ -n "$p" ] && elf_ok "$p"; then
        ok "$b is ELF64 little endian AArch64 PIE"
    else
        bad "$b ELF header check failed"
    fi
done

v="$("$WIT" --version 2>&1)"
case "$v" in
    *"Wiimms ISO Tool v3.01a r7464"*) ok "wit version banner: $v" ;;
    *) bad "wit version banner: $v" ;;
esac

v="$("$WWT" --version 2>&1)"
case "$v" in
    *"Wiimms WBFS Tool v3.01a r7464"*) ok "wwt version banner: $v" ;;
    *) bad "wwt version banner: $v" ;;
esac

v="$("$WDF" --version 2>&1)"
case "$v" in
    *"wdf v3.01a r7464"*) ok "wdf version banner: $v" ;;
    *) bad "wdf version banner: $v" ;;
esac

# ---- craft fixtures -------------------------------------------------------
WORK="$(mktemp -d 2>/dev/null || true)"
if [ -z "$WORK" ]; then
    WORK="./wit-test-work"
    mkdir -p "$WORK"
fi
cd "$WORK" || { echo "cannot enter workdir"; exit 1; }

# minimal raw Wii disc image: 64 KiB, disc id + Wii/GameCube magic words
dd if=/dev/zero of=mini.iso bs=1024 count=64 2>/dev/null
printf 'WITP01' | dd of=mini.iso bs=1 seek=0 conv=notrunc 2>/dev/null
printf '\x5d\x1c\x9e\xa3' | dd of=mini.iso bs=1 seek=24 conv=notrunc 2>/dev/null
printf '\xc2\x33\x9f\x3d' | dd of=mini.iso bs=1 seek=28 conv=notrunc 2>/dev/null

# minimal WDF v1 container wrapping mini.iso:
# 56 byte header + magic + 28 byte v1 chunk entry + payload
{
    printf 'WII\x01DISC'
    printf '\x00\x00\x00\x01'                       # wdf_version = 1
    printf '\x00\x00\x00\x38'                       # head_size = 56
    printf '\x00\x00\x00\x00'                       # align_factor = 0
    printf '\x00\x00\x00\x01'                       # wdf_compatible = 1
    printf '\x00\x00\x00\x00\x00\x01\x00\x00'       # file_size = 65536
    printf '\x00\x00\x00\x00\x00\x01\x00\x00'       # data_size = 65536
    printf '\x00\x00\x00\x00'                       # reserved = 0
    printf '\x00\x00\x00\x01'                       # chunk_n = 1
    printf '\x00\x00\x00\x00\x00\x00\x00\x38'       # chunk_off = 56
    printf 'WII\x01DISC'                            # magic again at chunk_off
    printf '\x00\x00\x00\x00'                       # ignored_split_file_index
    printf '\x00\x00\x00\x00\x00\x00\x00\x00'       # file_pos = 0
    printf '\x00\x00\x00\x00\x00\x00\x00\x5c'       # data_off = 92
    printf '\x00\x00\x00\x00\x00\x01\x00\x00'       # chunk data_size = 65536
} > mini.wdf
cat mini.iso >> mini.wdf

# control file: not a disc image
dd if=/dev/zero of=plain.bin bs=16 count=10 2>/dev/null
printf 'NOTADISC' | dd of=plain.bin bs=1 seek=0 conv=notrunc 2>/dev/null

set -- $(sha256sum mini.iso)
want_hash="$1"

# ---- wit FTYPE: magic based file type detection ---------------------------
out="$("$WIT" FTYPE mini.iso 2>&1)"
case "$out" in
    *"ISO/WII"*) ok "FTYPE detects raw Wii disc image (ISO/WII)" ;;
    *) bad "FTYPE mini.iso: $out" ;;
esac

out="$("$WIT" FTYPE mini.wdf 2>&1)"
case "$out" in
    *"WDF1/WII"*) ok "FTYPE detects WDF v1 container (WDF1/WII)" ;;
    *) bad "FTYPE mini.wdf: $out" ;;
esac

out="$("$WIT" FTYPE plain.bin 2>&1)"
case "$out" in
    *"OTHER"*) ok "FTYPE classifies non-disc file as OTHER" ;;
    *) bad "FTYPE plain.bin: $out" ;;
esac

out="$("$WIT" FTYPE no-such-file-xyz.iso 2>&1)"
case "$out" in
    *"NO-FILE"*) ok "FTYPE reports missing file as NO-FILE" ;;
    *) bad "FTYPE missing file: $out" ;;
esac

# ---- wdf +DUMP: parse the crafted WDF structure ----------------------------
out="$("$WDF" +DUMP mini.wdf 2>&1)"
case "$out" in
    *"WDF version       :          1/hex"*) ok "wdf +DUMP reports WDF version 1" ;;
    *) bad "wdf +DUMP WDF version: $out" ;;
esac
case "$out" in
    *"Number of chunks  :          1/hex"*) ok "wdf +DUMP reports 1 data chunk" ;;
    *) bad "wdf +DUMP chunk count: $out" ;;
esac

# ---- wdf +CAT: byte exact payload roundtrip --------------------------------
"$WDF" +CAT mini.wdf > cat.out 2>/dev/null
set -- $(sha256sum cat.out)
got_hash="$1"
if [ "$got_hash" = "$want_hash" ]; then
    ok "wdf +CAT payload roundtrip, sha256 $got_hash"
else
    bad "wdf +CAT roundtrip: got $got_hash want $want_hash"
fi

# ---- error path: wdf +DUMP on a missing file must fail ----------------------
if "$WDF" +DUMP no-such.wdf >/dev/null 2>&1; then
    bad "wdf +DUMP on missing file should fail"
else
    ok "wdf +DUMP on missing file exits with error"
fi

# ---- summary ----------------------------------------------------------------
echo
echo "passed: $pass  failed: $fail"
if [ "$fail" -eq 0 ]; then
    echo "ALL TESTS PASSED"
    exit 0
fi
echo "$fail TEST(S) FAILED"
exit 1
