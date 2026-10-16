#!/usr/bin/env bash
# test_package/test_ohos.sh — HarmonyOS-specific tests for indi-nexdome.
#
# Parameters: $1 = package folder of indi-nexdome.
#
# These assertions cover the parts of the adaptation that are specific to the
# HarmonyOS PC (aarch64) target and that the upstream test suite (nonexistent)
# could not cover: the OHOS ELF/ABI shape, the musl loader, the deliberately
# static INDI linkage (the libindi shared objects cannot be loaded on this
# target), the shipped device descriptor and a real execution of the driver on
# the device.
set -uo pipefail

PKG="${1:?usage: test_ohos.sh <package_folder>}"
BIN="$PKG/bin/indi_nexdome"
XML="$PKG/share/indi/indi_nexdome.xml"
[ -f "$BIN" ] || { echo "FAIL: driver binary not found: $BIN" >&2; exit 1; }

PASS=0
ok()   { echo "OK:   $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1" >&2; exit 1; }

TMP="$(mktemp -d 2>/dev/null || mktemp -d -t nd)" || TMP="./nd-ohos.$$"
mkdir -p "$TMP"
trap 'rm -rf "$TMP"' EXIT

readelf -h "$BIN" >"$TMP/eh" 2>/dev/null
readelf -d "$BIN" >"$TMP/ed" 2>/dev/null
readelf -SW "$BIN" >"$TMP/es" 2>/dev/null
readelf -lW "$BIN" >"$TMP/el" 2>/dev/null

# 1 -- running on the HarmonyOS platform
[ "$(uname -s)" = "HarmonyOS" ] || fail "1: not running on HarmonyOS"
ok "1: platform identity HarmonyOS"

# 2 -- aarch64 host/target
[ "$(uname -m)" = "aarch64" ] || fail "2: arch is not aarch64"
ok "2: platform architecture aarch64"

# 3 -- 64-bit ELF (LP64)
grep -q "ELF64" "$TMP/eh" || fail "3: not ELF64"
ok "3: artifact is ELF64 (LP64 data model)"

# 4 -- AArch64 machine
grep -q "AArch64" "$TMP/eh" || fail "4: machine is not AArch64"
ok "4: ELF machine type AArch64"

# 5 -- position independent executable
grep -q "DYN (Position-Independent Executable" "$TMP/eh" || fail "5: binary is not a PIE"
ok "5: ELF type DYN (PIE)"

# 6 -- OHOS musl interpreter
if grep -q "/lib/ld-musl-aarch64.so.1" "$TMP/el"; then
    ok "6: interpreter /lib/ld-musl-aarch64.so.1 (musl)"
else
    fail "6: musl interpreter missing"
fi

# 7 -- no glibc-only dependencies
for bad in "libm.so.6" "libpthread.so.0" "libdl.so.2" "libstdc++.so" "libgcc_s.so"; do
    grep -q "$bad" "$TMP/ed" && fail "7: glibc-only NEEDED entry: $bad"
done
ok "7: no glibc-only NEEDED entries"

# 8 -- the INDI framework is linked statically (its shared objects are not
#      loadable on this target, see notes.md)
for bad in "libindidriver.so" "libindiclient.so" "libindiAlignmentDriver.so"; do
    grep -q "$bad" "$TMP/ed" && fail "8: INDI still linked dynamically: $bad"
done
grep -q "NEEDED" "$TMP/ed" || fail "8: no dynamic section?"
ok "8: INDI framework statically linked (no libindi*.so in NEEDED)"

# 9 -- INDI framework code really present inside the binary
strings -a "$BIN" >"$TMP/str" 2>/dev/null || true
nm "$BIN" >"$TMP/nm" 2>/dev/null || true
grep -q "INDI Device driver framework." "$TMP/str" || fail "9: INDI framework not embedded"
grep -q "ISGetProperties" "$TMP/nm" || fail "9: INDI entry symbols missing"
ok "9: INDI framework embedded (driver main + ISGetProperties present)"

# 10 -- OHOS identity note section
grep -q "\.note\.ohos\.ident" "$TMP/es" || fail "10: .note.ohos.ident section missing"
ok "10: .note.ohos.ident section present"

# 11 -- the device descriptor is installed next to the binary
[ -f "$XML" ] || fail "11: $XML not installed"
grep -q "indi_nexdome" "$XML" || fail "11: descriptor does not name the driver"
ok "11: share/indi/indi_nexdome.xml installed and names indi_nexdome"

# 12 -- the driver really executes on this device and serves the INDI protocol
printf "<getProperties version='1.7'/>\n" | timeout 20 "$BIN" >"$TMP/gp" 2>"$TMP/err"
grep -q "device='NexDome'" "$TMP/gp" || fail "12: driver did not answer getProperties"
ok "12: driver executes on OHOS and serves the INDI protocol"

echo "PASS: test_ohos.sh $PASS/12"
