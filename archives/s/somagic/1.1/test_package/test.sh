#!/data/service/hnp/bin/bash
# test_package/test.sh — somagic 1.1 consumer verification
#
# somagic ships four command-line tools (no library, no public headers), so the
# consumer is whoever installs the package and runs those tools. Every check
# below executes an *installed* executable and asserts on real output (R34):
#
#   * --version / --help banners on the three tools that implement them;
#   * somagic-init firmware paths: default firmware open failure, then a real
#     libgcrypt GCRY_MD_CRC32 validation of a fixture file ("was not
#     recognized"), then the --skip-check -f path, which goes through the real
#     libusb_init()/device-enumeration code. On this kernel netlink sockets are
#     unavailable, so libusb_init() fails; the portability patch makes that a
#     clean diagnostic + exit 1 instead of the previous SIGSEGV (exit 139).
#   * somagic-capture argument validation and its device-free path (same
#     libusb_init guard);
#   * somagic-audio-capture is the device-only beta program whose main()
#     asserts on a device handle immediately; it is verified as a packaged,
#     executable ELF instead of being run (running it without hardware aborts
#     by upstream design).
#
# Upstream has no automated test suite (the Makefile defines only
# all/beta/install/install-beta/clean; the tarball has no tests/ directory), so
# the upstream marker is emitted as no_tests with the audit reason. See
# test_package/MANIFEST.yml for the full audit.

# Wrapped in bash by test_package/conanfile.py (OHOS /system/bin/sh is mksh and
# cannot launch ELF binaries).
set -u

DISCOVERED=0
PASSED=0
FAILED=0

pass() {
    DISCOVERED=$((DISCOVERED + 1))
    PASSED=$((PASSED + 1))
    echo "[OK]   $1"
}

fail() {
    DISCOVERED=$((DISCOVERED + 1))
    FAILED=$((FAILED + 1))
    echo "[FAIL] $1"
}

# run <output-file> <command...>: run the command, echo its exit code.
run_capture() {
    local out="$1"; shift
    "$@" >"$out" 2>&1
    echo $?
}

BIN_DIR="${1:-}"
if [ -z "$BIN_DIR" ]; then
    # Fall back to the package bin dir exposed by the run environment.
    BIN_DIR="$(dirname "$(command -v somagic-init)")"
fi
echo "--- somagic 1.1 consumer verification (bin dir: $BIN_DIR) ---"

INIT="$BIN_DIR/somagic-init"
CAPTURE="$BIN_DIR/somagic-capture"
AUDIO="$BIN_DIR/somagic-audio-capture"
BOTH="$BIN_DIR/somagic-both"

# ---- 0. every documented executable is present and executable --------------
for exe in "$INIT" "$CAPTURE" "$AUDIO" "$BOTH"; do
    name="$(basename "$exe")"
    if [ -x "$exe" ]; then
        pass "$name is present and executable"
    else
        fail "$name missing or not executable ($exe)"
    fi
done

# /tmp is read-only on this platform, so probe TMPDIR, the injected temp dir and
# finally the current directory instead of relying on mktemp defaults.
WORK=""
for base in "${TMPDIR:-}" "${TMP:-}" "${TEMP:-}" "$(pwd)"; do
    [ -n "$base" ] || continue
    [ -d "$base" ] || continue
    candidate="$base/somagic-consumer-$$"
    if mkdir -p "$candidate" 2>/dev/null && touch "$candidate/.probe" 2>/dev/null; then
        rm -f "$candidate/.probe"
        WORK="$candidate"
        break
    fi
done
if [ -z "$WORK" ]; then
    WORK="$(pwd)"
fi
cleanup() { [ -n "$WORK" ] && rm -rf "$WORK"; }
trap cleanup EXIT

# A short fixture with an arbitrary CRC32, used to drive somagic-init's real
# libgcrypt firmware validation path without needing the proprietary firmware.
FIXTURE="$WORK/firmware.bin"
printf 'AAAA' >"$FIXTURE"

# ---- 1. somagic-init --version --------------------------------------------
rc=$(run_capture "$WORK/out" "$INIT" --version)
if [ "$rc" = "0" ] && grep -q "somagic-init 1.1" "$WORK/out"; then
    pass "somagic-init --version -> $(tr '\n' ' ' <"$WORK/out")"
else
    fail "somagic-init --version rc=$rc output=[$(tr '\n' ' ' <"$WORK/out")]"
fi

# ---- 2. somagic-init --help ------------------------------------------------
rc=$(run_capture "$WORK/out" "$INIT" --help)
if [ "$rc" = "0" ] && grep -q "Usage: somagic-init" "$WORK/out"; then
    pass "somagic-init --help lists usage"
else
    fail "somagic-init --help rc=$rc output=[$(tr '\n' ' ' <"$WORK/out")]"
fi

# ---- 3. somagic-init default firmware path --------------------------------
# No --firmware: the compiled-in default /lib/firmware/somagic_firmware.bin is
# absent, so the tool reports the open failure and exits 1.
rc=$(run_capture "$WORK/out" "$INIT")
if [ "$rc" = "1" ] && grep -q "Failed to open firmware file" "$WORK/out"; then
    pass "somagic-init bare run reports default firmware open failure"
else
    fail "somagic-init bare run rc=$rc output=[$(tr '\n' ' ' <"$WORK/out")]"
fi

# ---- 4. libgcrypt GCRY_MD_CRC32 firmware validation -----------------------
# -f with a fixture: the file is read and its CRC32 (libgcrypt) is compared to
# the three known firmware digests -> not recognized, exit 1.
rc=$(run_capture "$WORK/out" "$INIT" -f "$FIXTURE")
if [ "$rc" = "1" ] && grep -q "was not recognized" "$WORK/out"; then
    pass "somagic-init validates firmware CRC via libgcrypt (fixture rejected)"
else
    fail "somagic-init -f fixture rc=$rc output=[$(tr '\n' ' ' <"$WORK/out")]"
fi

# ---- 5. libusb-1.0 init / device enumeration path -------------------------
# --skip-check skips the CRC and goes straight to libusb_init + find_device.
# On this kernel the netlink hotplug socket is unavailable, so libusb_init()
# fails; the patched guard reports it and exits 1 (previously: SIGSEGV/139).
# Where libusb init succeeds, the deterministic 1c88:0007 not-found path runs.
# Either way the process must terminate with exit code 1 and never a signal.
rc=$(run_capture "$WORK/out" "$INIT" --skip-check -f "$FIXTURE")
if [ "$rc" = "1" ] && { grep -q "Failed to initialize libusb" "$WORK/out" \
        || grep -q "USB device 1c88:0007 was not found" "$WORK/out"; }; then
    pass "somagic-init --skip-check exits 1 without crashing (libusb_init/enumeration path)"
else
    fail "somagic-init --skip-check rc=$rc output=[$(tr '\n' ' ' <"$WORK/out")]"
fi

# ---- 6. somagic-capture --version -----------------------------------------
rc=$(run_capture "$WORK/out" "$CAPTURE" --version)
if [ "$rc" = "0" ] && grep -q "somagic-capture 1.1" "$WORK/out"; then
    pass "somagic-capture --version -> $(tr '\n' ' ' <"$WORK/out")"
else
    fail "somagic-capture --version rc=$rc output=[$(tr '\n' ' ' <"$WORK/out")]"
fi

# ---- 7. somagic-capture --help --------------------------------------------
rc=$(run_capture "$WORK/out" "$CAPTURE" --help)
if [ "$rc" = "0" ] && grep -q "Usage: somagic-capture" "$WORK/out"; then
    pass "somagic-capture --help lists usage"
else
    fail "somagic-capture --help rc=$rc output=[$(tr '\n' ' ' <"$WORK/out")]"
fi

# ---- 8. somagic-capture argument validation -------------------------------
rc=$(run_capture "$WORK/out" "$CAPTURE" -B 999)
if [ "$rc" = "1" ] && grep -q "Invalid brightness value" "$WORK/out"; then
    pass "somagic-capture rejects out-of-range brightness"
else
    fail "somagic-capture -B 999 rc=$rc output=[$(tr '\n' ' ' <"$WORK/out")]"
fi

# ---- 9. somagic-capture device-free path ----------------------------------
# Either the libusb_init guard fires, or the device-free enumeration reports
# the uninitialized device. Both are a clean exit 1; never a signal.
rc=$(run_capture "$WORK/out" "$CAPTURE")
if [ "$rc" = "1" ] && { grep -q "Failed to initialize libusb" "$WORK/out" \
        || grep -q "Has device initialization been performed" "$WORK/out"; }; then
    pass "somagic-capture bare run exits 1 without crashing"
else
    fail "somagic-capture bare run rc=$rc output=[$(tr '\n' ' ' <"$WORK/out")]"
fi

# ---- 10. somagic-both --version -------------------------------------------
# The beta tool prints the shared "capture 1.0" banner.
rc=$(run_capture "$WORK/out" "$BOTH" --version)
if [ "$rc" = "0" ] && grep -q "capture 1.0" "$WORK/out"; then
    pass "somagic-both --version -> $(tr '\n' ' ' <"$WORK/out")"
else
    fail "somagic-both --version rc=$rc output=[$(tr '\n' ' ' <"$WORK/out")]"
fi

# ---- 11. somagic-both --help ----------------------------------------------
rc=$(run_capture "$WORK/out" "$BOTH" --help)
if [ "$rc" = "0" ] && grep -q "Usage: capture" "$WORK/out"; then
    pass "somagic-both --help lists usage"
else
    fail "somagic-both --help rc=$rc output=[$(tr '\n' ' ' <"$WORK/out")]"
fi

# ---- 12. somagic-audio-capture packaged as an executable ELF --------------
# Device-only beta: main() has no CLI and asserts on the device handle, so it
# cannot run without hardware. Verify the packaged artifact is a real ELF
# executable instead.
elf_magic="$(printf '\177ELF')"
actual_magic="$(head -c 4 "$AUDIO" 2>/dev/null)"
if [ -x "$AUDIO" ] && [ "$actual_magic" = "$elf_magic" ]; then
    pass "somagic-audio-capture is a packaged executable ELF"
else
    fail "somagic-audio-capture is not an executable ELF"
fi

echo "--- somagic consumer: $DISCOVERED checks run, $PASSED passed, $FAILED failed ---"

if [ "$FAILED" -eq 0 ]; then
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test.sh","discovered":%d,"passedCount":%d}\n' \
        "$DISCOVERED" "$PASSED"
else
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"bash test.sh","discovered":%d,"passedCount":%d}\n' \
        "$DISCOVERED" "$PASSED"
fi

printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"somagic 1.1 (easycap-somagic-linux) ships no automated test suite: the raw Makefile defines only all/beta/install/install-beta/clean targets (no check/test target) and the tarball has no tests/ directory, so there is no upstream test suite to run. See test_package/MANIFEST.yml upstream_test_audit for the full audit."}\n'

[ "$FAILED" -eq 0 ] || exit 1
echo "ALL CHECKS PASSED"
exit 0
