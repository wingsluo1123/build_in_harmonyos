#!/bin/sh
# test_package/test.sh — consumer smoke test for the packaged yutu executable.
#
# Nine explicit assertions (kept in sync with MANIFEST.yml assertion_count).
# Usage: sh test.sh <path-to-yutu>
set -eu

# HMBS injects TMPDIR/TMP/TEMP; cd there so the shell is not left in an HMDFS
# cwd that breaks getcwd on HNP bash.
cd "${TMPDIR:-${TMP:-${TEMP:-/tmp}}}" 2>/dev/null || cd /tmp 2>/dev/null || true

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-yutu>" >&2
    exit 2
fi

yutu_bin="$1"
fail() { echo "        [FAIL] $1" >&2; exit 1; }

# ── 1. packaged artefact is an ELF executable ───────────────────────────────
[ -f "$yutu_bin" ] || fail "yutu binary not found: $yutu_bin"
magic=$(od -An -tx1 -N4 "$yutu_bin" | tr -d ' \n')
[ "$magic" = "7f454c46" ] || fail "not an ELF binary (magic=$magic)"
echo "[1/9] ELF magic ok ($magic)"

# ── 2/3/4. version banner ───────────────────────────────────────────────────
version_output="$("$yutu_bin" version 2>&1)" || fail "yutu version exited non-zero"
echo "[2/9] yutu version exit 0"
echo "      $version_output"
printf '%s\n' "$version_output" | grep -F "v0.10.9" >/dev/null \
    || fail "version banner does not report v0.10.9"
echo "[3/9] version banner reports v0.10.9"
printf '%s\n' "$version_output" | grep -F "linux/arm64" >/dev/null \
    || fail "version banner does not report linux/arm64"
echo "[4/9] version banner reports linux/arm64"

# ── 5/6/7. help listing ─────────────────────────────────────────────────────
help_output="$("$yutu_bin" help 2>&1)" || fail "yutu help exited non-zero"
echo "[5/9] yutu help exit 0"
printf '%s\n' "$help_output" | grep -F "video" >/dev/null \
    || fail "help listing does not expose the video command group"
echo "[6/9] help exposes 'video'"
printf '%s\n' "$help_output" | grep -F "playlist" >/dev/null \
    || fail "help listing does not expose the playlist command group"
echo "[7/9] help exposes 'playlist'"

# ── 8. a real subcommand parses ─────────────────────────────────────────────
"$yutu_bin" video --help >/dev/null 2>&1 || fail "yutu video --help exited non-zero"
echo "[8/9] yutu video --help exit 0"

# ── 9. statically linked (upstream builds FROM scratch) ─────────────────────
if command -v llvm-readelf >/dev/null 2>&1; then
    readelf_bin=llvm-readelf
elif command -v readelf >/dev/null 2>&1; then
    readelf_bin=readelf
else
    readelf_bin=""
fi
if [ -n "$readelf_bin" ]; then
    if "$readelf_bin" -d "$yutu_bin" 2>/dev/null | grep -q "NEEDED"; then
        fail "binary is dynamically linked (DT_NEEDED present)"
    fi
    echo "[9/9] statically linked (no DT_NEEDED)"
else
    # Fall back to a byte-level probe: a dynamically linked ELF carries the
    # interpreter path "/lib/ld-" in .interp.
    if od -c "$yutu_bin" 2>/dev/null | grep -q "ld-linux"; then
        fail "binary looks dynamically linked (.interp present)"
    fi
    echo "[9/9] statically linked (no .interp found, readelf unavailable)"
fi

echo "[ok] All 9 consumer smoke assertions passed."
