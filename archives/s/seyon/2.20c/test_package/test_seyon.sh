#!/bin/sh
# test_seyon.sh — verify the packaged seyon artifacts work on HarmonyOS.
#
# Called by test_package/conanfile.py test() with:
#   $1 = package bin/ directory      (contains seyon)
#   $2 = package lib/ directory      (contains libseyon.a)
#   $3 = package include/ directory  (contains seyon/ headers)
#   $4 = package share/seyon/ dir    (contains seyon.help)
#   $5 = optional colon-joined LD_PRELOAD list of runtime .so paths
#        (HMBS [stale_runtime_library]: the loader may ignore
#        LD_LIBRARY_PATH, so absolute paths are preloaded as a fallback;
#        xcdplayer/xeyes precedent).
#
# POSIX sh only (HMBS [shell_getcwd]: run with injected SHELL=/bin/sh).
# No set -e/-u/pipefail: toybox ash rejects them; every assertion captures its
# own rc and always prints output so loader errors reach the log.

BIN_DIR="$1"
LIB_DIR="$2"
INC_DIR="$3"
SHARE_DIR="$4"
LD_PRELOAD_EXTRA="${5:-}"

SEYON_BIN="$BIN_DIR/seyon"

if [ -z "$SEYON_BIN" ] || [ ! -x "$SEYON_BIN" ]; then
    echo "FAIL: seyon binary not found or not executable: $SEYON_BIN"
    exit 1
fi

export LD_LIBRARY_PATH="${BIN_DIR}:${LD_LIBRARY_PATH:-}"
if [ -n "$LD_PRELOAD_EXTRA" ]; then
    export LD_PRELOAD="$LD_PRELOAD_EXTRA"
fi

echo "[shell] $0"
echo "[env] LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "[env] LD_PRELOAD=${LD_PRELOAD:-}"

# pick a readelf: llvm-readelf (OHOS SDK) then GNU readelf
READELF=""
for c in llvm-readelf readelf /data/service/hnp/bin/llvm-readelf; do
    if command -v "$c" >/dev/null 2>&1; then READELF="$c"; break; fi
done

discovered=8
passed=0

echo "[test 1/$discovered] seyon is an ELF binary"
if head -c 4 "$SEYON_BIN" | od -An -tx1 | grep -q '7f 45 4c 46'; then
    echo "PASS: seyon is an ELF binary"
    passed=$((passed + 1))
else
    echo "FAIL: seyon does not look like an ELF binary"
fi

echo "[test 2/$discovered] seyon runs headless: -noemulator + no DISPLAY -> 'Can't open display'"
# seyon's main() otherwise wraps itself in a terminal emulator (xterm). With
# -noemulator it reaches XtAppInitialize directly; with an empty DISPLAY libXt
# fails to open the display. Reaching that message proves the whole dynamic
# link chain (libXaw/libXmu/libXt/libX11/...) resolved.
out=$(DISPLAY= "$SEYON_BIN" -noemulator 2>&1)
rc=$?
echo "$out"
echo "exit=$rc"
if echo "$out" | grep -q "Can't open display"; then
    echo "PASS: seyon reports \"Can't open display\" without DISPLAY"
    passed=$((passed + 1))
else
    echo "FAIL: expected \"Can't open display\" on stderr"
fi

echo "[test 3/$discovered] exit code is 1 on missing display"
if [ "$rc" -eq 1 ]; then
    echo "PASS: exit code is 1 on missing display"
    passed=$((passed + 1))
else
    echo "FAIL: expected exit 1, got $rc"
fi

echo "[test 4/$discovered] static library libseyon.a installed"
if [ -f "$LIB_DIR/libseyon.a" ]; then
    echo "PASS: libseyon.a installed"
    passed=$((passed + 1))
else
    echo "FAIL: libseyon.a missing from $LIB_DIR"
fi

echo "[test 5/$discovered] seyon headers installed"
if [ -f "$INC_DIR/seyon/seyon.h" ] && [ -f "$INC_DIR/seyon/SeParse.h" ]; then
    echo "PASS: seyon headers installed"
    passed=$((passed + 1))
else
    echo "FAIL: seyon headers missing from $INC_DIR/seyon/"
fi

echo "[test 6/$discovered] help file installed"
if [ -f "$SHARE_DIR/seyon.help" ]; then
    echo "PASS: seyon.help installed"
    passed=$((passed + 1))
else
    echo "FAIL: seyon.help missing from $SHARE_DIR"
fi

echo "[test 7/$discovered] DT_NEEDED points at the conan X11 stack"
if [ -n "$READELF" ]; then
    needed=$("$READELF" -d "$SEYON_BIN" 2>/dev/null | grep NEEDED)
    echo "$needed"
    if echo "$needed" | grep -q "libXaw.so" && \
       echo "$needed" | grep -q "libXt.so" && \
       echo "$needed" | grep -q "libX11.so"; then
        echo "PASS: seyon is dynamically linked against libXaw/libXt/libX11"
        passed=$((passed + 1))
    else
        echo "FAIL: expected DT_NEEDED libXaw/libXt/libX11"
    fi
else
    echo "FAIL: no readelf available to check DT_NEEDED"
fi

echo "[test 8/$discovered] every packaged ELF has exactly one .codesign section"
if [ -n "$READELF" ]; then
    sign_ok=1
    for elf in "$BIN_DIR"/*; do
        [ -f "$elf" ] || continue
        head -c 4 "$elf" | od -An -tx1 | grep -q '7f 45 4c 46' || continue
        cnt=$("$READELF" -SW "$elf" 2>/dev/null | grep -c '\.codesign')
        echo "  $elf: .codesign sections = $cnt"
        if [ "$cnt" -ne 1 ]; then sign_ok=0; fi
    done
    if [ "$sign_ok" -eq 1 ]; then
        echo "PASS: all packaged ELF binaries carry exactly one .codesign section"
        passed=$((passed + 1))
    else
        echo "FAIL: a packaged ELF does not have exactly one .codesign section"
    fi
else
    echo "FAIL: no readelf available to check .codesign"
fi

if [ "$passed" -ne "$discovered" ]; then
    echo "FAIL: $((discovered - passed))/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_seyon.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_seyon.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
exit 0
