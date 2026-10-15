#!/usr/bin/env bash
# test_package/test.sh — consumer smoke test for the packaged yatas executable.
# yatas (padok-team/yatas) is a Go CLI: `--help` prints flag usage and exits 0,
# `--init` writes a `.yatas.yml` config into the current directory.
# Asserts (5):
#   1. yatas binary exists and is executable
#   2. `yatas --help` exits 0
#   3. `--help` output is non-empty and lists core flags (--init / --readme)
#   4. `yatas --init` exits 0 and writes a config file
#   5. `.yatas.yml` was actually created by `--init`
set -euo pipefail

# HMBS injects TMPDIR/TMP/TEMP; cd there so the shell is not left in an HMDFS
# cwd that breaks getcwd (`[shell_getcwd]` diagnostic).
cd "${TMPDIR:-${TMP:-${TEMP:-/tmp}}}" 2>/dev/null || cd /tmp 2>/dev/null || true

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-yatas>" >&2
    exit 2
fi

yatas_bin="$1"

if [ ! -f "$yatas_bin" ]; then
    echo "yatas binary not found: $yatas_bin" >&2
    exit 1
fi
echo "[step 1] yatas binary exists: $yatas_bin"

# Resolve an exec-able copy of the packaged binary. On OHOS the conan package
# cache may be mounted noexec (ohpcd CI worker "Operation not permitted" when
# exec'ing the packaged binary directly, while upstream test binaries exec fine
# from the writable ext2 workspace). Try the packaged path first (works on
# normally-exec-able filesystems); if exec fails with a permission error, fall
# back to an identical byte-copy in the current writable workdir (HMBS-injected
# TMPDIR), which preserves the .codesign section so OHOS can exec it.
RUN_BIN="$yatas_bin"
if ! "$RUN_BIN" --help >/dev/null 2>&1; then
    copy_dst="$PWD/yatas-exec-$$"
    cp -f "$yatas_bin" "$copy_dst" 2>/dev/null || true
    chmod 755 "$copy_dst" 2>/dev/null || true
    if [ -f "$copy_dst" ] && "$copy_dst" --help >/dev/null 2>&1; then
        echo "[step 1] packaged binary not directly exec-able; using writable copy: $copy_dst"
        RUN_BIN="$copy_dst"
    else
        rm -f "$copy_dst"
        RUN_BIN="$yatas_bin"
    fi
fi

echo "[step 2] Testing yatas --help..."
set +e
help_output="$("$RUN_BIN" --help 2>&1)"
help_rc=$?
set -e
echo "        [info] --help exit code: $help_rc"
echo "        [info] --help output:"
printf '%s\n' "$help_output" | sed 's/^/          /'
[ "$help_rc" -eq 0 ]
echo "        [ok] --help exits 0"

echo "[step 3] Checking --help lists core flags..."
if [ -z "$help_output" ]; then
    echo "        [fail] --help produced empty output" >&2
    exit 1
fi
# yatas uses Go's standard flag package, which prints single-dash flags
# (-init / -readme / -install / ...) in its usage text. Match the single-dash
# forms (Go also accepts --init/--readme on the command line, but the help
# output is single-dash, so grep for the actual printed spelling).
grep -qE -- "(-init|-readme|-install|-only-failure)" <<<"$help_output"
echo "        [ok] --help lists core flags"

echo "[step 4] Testing yatas --init (writes config into a temp workdir)..."
workdir="${TMPDIR:-${TMP:-${TEMP:-/tmp}}}/yatas-test-$$"
rm -rf "$workdir"
mkdir -p "$workdir"
set +e
(
    cd "$workdir"
    "$RUN_BIN" --init > init.out 2>&1
)
init_rc=$?
set -e
echo "        [info] --init exit code: $init_rc"
echo "        [info] --init output:"
cat "$workdir/init.out" 2>/dev/null | sed 's/^/          /'
[ "$init_rc" -eq 0 ]
echo "        [ok] --init exits 0"

echo "[step 5] Checking .yatas.yml was created..."
if [ ! -s "$workdir/.yatas.yml" ]; then
    echo "        [fail] --init did not create .yatas.yml in $workdir" >&2
    ls -la "$workdir" 2>/dev/null || true
    rm -rf "$workdir"
    exit 1
fi
echo "        [ok] .yatas.yml created (non-empty)"
rm -rf "$workdir"

echo "[ok] All tests passed."
