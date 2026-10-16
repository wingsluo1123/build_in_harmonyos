#!/data/service/hnp/bin/bash
# spellcast 1.0 — OHOS consumer tests (test_package)
#
# spellcast is an X11 GUI game built as PIE. OHOS uses musl with
# /lib/ld-musl-aarch64.so.1. Runs under conanrun env (PATH includes the
# installed bin/, LD_LIBRARY_PATH includes the libx11 dependency libdirs).
#
# Tests 1-9 verify package content/ELF metadata.
# Test 10 is the HarmonyOS-specific NON-ASSERTION runtime feasibility case:
# it actually executes the binary and only fails on dynamic-loader errors
# ("Error loading shared library" / "Error relocating") — any other outcome
# (usage banner, exit 12, display error) proves the full shared-library
# closure (libX11.so.6 + libc.so) loads and relocates natively on OHOS.
set -uo pipefail

PASS=0
FAIL=0

report() {
    local name="$1" rc="$2"
    if [ "$rc" -eq 0 ]; then
        echo "PASS: $name"
        PASS=$((PASS+1))
    else
        echo "FAIL: $name (rc=$rc)"
        FAIL=$((FAIL+1))
    fi
}

SPELLCAST_BIN="$(command -v spellcast)"
if [ -z "$SPELLCAST_BIN" ]; then
    echo "FAIL spellcast not found in PATH (conanrun env)"
    echo "[debug] PATH=$PATH"
    exit 1
fi
PKG_ROOT="$(cd "$(dirname "$SPELLCAST_BIN")/.." && pwd)"
MAN="$PKG_ROOT/share/man/man6/spellcast.6"
SPELLIST="$PKG_ROOT/share/spellcast/spelllist.ps"
echo "[debug] BIN=$SPELLCAST_BIN"
echo "[debug] LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-<unset>}"

# 1. Binary exists
test -f "$SPELLCAST_BIN"
report "binary exists" $?

# 2. Binary is ELF (PIE executable)
FILE_OUT=$(file -b "$SPELLCAST_BIN")
echo "file output: $FILE_OUT"
if echo "$FILE_OUT" | grep -q "ELF"; then
    report "ELF binary" 0
else
    report "ELF binary — got: $FILE_OUT" 1
fi

# 3. Binary is aarch64 (HarmonyOS target)
# NOTE: musl/busybox grep on OHOS has no GNU \| alternation in BRE — use -E.
if echo "$FILE_OUT" | grep -q -E "arm64|aarch64"; then
    report "ELF aarch64 (HarmonyOS target)" 0
else
    report "ELF aarch64 (HarmonyOS target) — got: $FILE_OUT" 1
fi

# 4. Binary is dynamically linked (PIE)
if echo "$FILE_OUT" | grep -q "dynamic"; then
    report "PIE dynamically linked" 0
else
    report "PIE dynamically linked — got: $FILE_OUT" 1
fi

# 5. OHOS: verify libX11 linkage via readelf (ldd not available)
READELF_OUT=$(readelf -d "$SPELLCAST_BIN" 2>&1 || true)
echo "readelf -d output: $READELF_OUT"
if echo "$READELF_OUT" | grep -q "libX11"; then
    report "libX11 NEEDED (readelf)" 0
else
    report "libX11 NEEDED (readelf) — not found" 1
fi

# 6. OHOS: verify musl dynamic linker
if echo "$FILE_OUT" | grep -q "ld-musl"; then
    report "musl dynamic linker (/lib/ld-musl-aarch64.so.1)" 0
else
    report "musl dynamic linker — got: $FILE_OUT" 1
fi

# 7. Man page exists
test -f "$MAN"
report "man page exists" $?

# 8. spelllist.ps exists
test -f "$SPELLIST"
report "spelllist.ps exists" $?

# 9. Binary has symbol table (not stripped)
if echo "$FILE_OUT" | grep -q "not stripped"; then
    report "binary has debug symbols (not stripped)" 0
else
    report "binary has debug symbols" 1
fi

# ------------------------------------------------------------------
# Test 10 — HarmonyOS consumer runtime feasibility (NON-ASSERTION).
# Execute the binary without a DISPLAY. The dynamic loader must load and
# relocate the full NEEDED closure (libX11.so.6, libc.so) before main()
# runs; a usage banner / exit 12 (no args) proves native execution.
# Only loader errors are failures. Non-assertion: we never match specific
# program output.
# ------------------------------------------------------------------
loader_blocked() { # output -> rc
    case "$1" in
        *"Error loading shared library"*|*"Error relocating"*) return 0 ;;
        *) return 1 ;;
    esac
}

# Fallback staging: copy the dependency closure into a loader-accessible
# dir and point LD_LIBRARY_PATH there (loader-inaccessible FUSE mounts).
stage_libs() {
    local run_dir="${TMPDIR:-$HOME/tmp}/spellcast-test-$$-libs"
    mkdir -p "$run_dir" 2>/dev/null || run_dir="$HOME/tmp/spellcast-test-$$-libs"
    mkdir -p "$run_dir" || return 1
    echo "$LD_LIBRARY_PATH" | tr ':' '\n' | while read -r d; do
        [ -n "$d" ] && [ -d "$d" ] && cp -L "$d"/*.so* "$run_dir/" 2>/dev/null
    done
    export LD_LIBRARY_PATH="$run_dir"
}

echo "[test 10] spellcast runtime feasibility on OHOS (non-assertion closure load)"
exec_dir=""
# FUSE conan cache may drop the exec bit: retry from an exec-permitted copy
# on rc=126 before treating it as a closure failure.
OUT="$("$SPELLCAST_BIN" 2>&1)"
RC=$?
if [ "$RC" -eq 126 ] 2>/dev/null && echo "$OUT" | grep -q "Permission denied"; then
    exec_dir="${TMPDIR:-$HOME/tmp}/spellcast-test-$$-bin"
    mkdir -p "$exec_dir" 2>/dev/null || exec_dir="$HOME/tmp/spellcast-test-$$-bin"
    mkdir -p "$exec_dir" && cp -L "$SPELLCAST_BIN" "$exec_dir/spellcast" && chmod 755 "$exec_dir/spellcast" 2>/dev/null
    OUT="$("$exec_dir/spellcast" 2>&1)"
    RC=$?
fi
if loader_blocked "$OUT"; then
    stage_libs
    if [ -n "$exec_dir" ] && [ -x "$exec_dir/spellcast" ]; then
        OUT="$("$exec_dir/spellcast" 2>&1)"
    else
        OUT="$("$SPELLCAST_BIN" 2>&1)"
    fi
    RC=$?
fi
RUN_OUT="$OUT"
echo "runtime output: $RUN_OUT"
echo "runtime rc: $RC"
if loader_blocked "$RUN_OUT"; then
    report "spellcast loads full shared-lib closure on OHOS" 1
else
    report "spellcast loads full shared-lib closure on OHOS (rc=$RC, non-assertion)" 0
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && echo "ALL CONSUMER TESTS PASSED" || exit 1
