#!/usr/bin/env bash
# test_package/test.sh — smoke tests for irony-server
# Runs in conanrun env (PATH includes installed bin/, LD_LIBRARY_PATH
# includes the system SDK llvm libdir so libclang.so resolves).
set -eu

# OHOS has no /tmp; upstream TemporaryFile falls back to /tmp when
# TMPDIR/TMP/TEMP/TEMPDIR are all unset. Point TMPDIR at a writable dir.
export TMPDIR="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMPDIR"

echo "[test] irony-server --version"
OUTPUT="$(irony-server --version)"
echo "$OUTPUT"

# Line 1 must be "irony-server version 1.6.1" (compile-time
# IRONY_PACKAGE_VERSION, derived by CMake from ../irony.el — this proves
# the tarball layout held during the build).
echo "$OUTPUT" | grep -q "^irony-server version 1\.6\.1$"

# Line 2 is the clang version string reported by libclang AT RUNTIME —
# this proves libclang.so (system SDK) was found and loaded via
# LD_LIBRARY_PATH (a broken linkage would fail the binary outright).
echo "$OUTPUT" | sed -n 2p | grep -qi "clang version"

echo "[test] TU parse smoke (clang builtin headers / resource dir)"
# Parse real translation units through irony-server's interactive line
# protocol (parse FILE [-- FLAGS] / diagnostics / exit). A TU including a
# clang builtin header (<stddef.h>) can only parse when the resource dir is
# available at runtime — the exact failure mode TUManager's
# CLANG_RESOURCE_DIR guards against ("'stddef.h' file not found").
WORK="${TMPDIR}/irony-tu-smoke-$$"
mkdir -p "$WORK"
printf '#include <stddef.h>\nint main(void){ size_t x = 42; return (int)x - 42; }\n' > "$WORK/tu.c"
printf '#include <stddef.h>\nint main(void){ undefined_symbol_xyz; }\n' > "$WORK/tu_bad.c"

run_parse() {
    printf 'parse %s --\ndiagnostics\nexit\n' "$1" | irony-server -i 2>/dev/null
}

# Negative control: a TU referencing an undeclared symbol MUST produce an
# error diagnostic — proves the server really parses (no vacuous pass).
BAD_OUT="$(run_parse "$WORK/tu_bad.c")"
echo "$BAD_OUT"
echo "$BAD_OUT" | grep -qF 'use of undeclared identifier' || {
    echo "FAIL: negative control produced no diagnostic (parse pipeline broken)"
    exit 1
}

# The clean TU (stddef.h + size_t) must parse with zero error diagnostics.
GOOD_OUT="$(run_parse "$WORK/tu.c")"
echo "$GOOD_OUT"
if echo "$GOOD_OUT" | grep -qF ' error "'; then
    echo "FAIL: clean TU produced error diagnostics (clang resource dir broken at runtime?)"
    exit 1
fi

echo "OK: irony-server parsed a TU cleanly (builtin headers found); negative control errored as expected"
