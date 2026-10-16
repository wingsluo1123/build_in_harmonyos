#!/usr/bin/env bash
# test_package/test.sh — indi-nexdome functional (consumer-view) tests.
#
# Parameters: $1 = path of the installed indi_nexdome driver binary.
#
# The driver is an INDI device server: indiserver spawns it and talks the INDI
# XML protocol over stdin/stdout.  These tests therefore drive the real
# executable exactly the way its upstream consumers do.
#
# Assertions (7):
#   1  `indi_nexdome -h`   prints the framework usage and exits 1
#   2  empty stdin          starts the INDI event loop, exits cleanly on EOF
#   3  unknown option `-z` prints the framework usage and exits 1
#   4  `<getProperties/>`  -> the driver declares the NexDome device
#   5  DRIVER_INFO         -> DRIVER_NAME=NexDome / DRIVER_EXEC=indi_nexdome /
#                              DRIVER_VERSION=1.6
#   6  CONNECTION vector   -> CONNECT/DISCONNECT switches are defined
#   7  CONNECT request     -> answered with a CONNECTION setSwitchVector in the
#                              Alert state (no NexDome hardware on the host)
set -uo pipefail

BIN="${1:-indi_nexdome}"
[ -f "$BIN" ] || { echo "FAIL: driver binary not found: $BIN" >&2; exit 1; }

PASS=0
ok()   { echo "OK:   $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1" >&2; exit 1; }

TMP="$(mktemp -d 2>/dev/null || mktemp -d -t nd)" || TMP="./nd-test.$$"
mkdir -p "$TMP"
trap 'rm -rf "$TMP"' EXIT

usage_of() { "$BIN" "$@" >"$TMP/out" 2>&1; echo $?; }

# 1 -- -h prints the framework usage and exits 1
RC="$(usage_of -h)"
grep -q "Usage: .*indi_nexdome \[options\]" "$TMP/out" || fail "1: usage header missing"
grep -q "INDI Device driver framework."      "$TMP/out" || fail "1: framework banner missing"
grep -q -- "-v    : more verbose"            "$TMP/out" || fail "1: option list missing"
[ "$RC" -eq 1 ] || fail "1: expected exit 1, got $RC"
ok "1: -h prints the INDI driver usage and exits 1"

# 2 -- empty stdin: the driver enters its event loop and exits cleanly on EOF
printf '' | timeout 20 "$BIN" >"$TMP/out" 2>&1
RC=$?
grep -q "indi_nexdome: EOF" "$TMP/out" || fail "2: driver did not start its INDI event loop"
[ "$RC" -eq 1 ] || fail "2: expected exit 1 on EOF, got $RC"
ok "2: empty stdin starts the INDI event loop and exits cleanly on EOF"

# 3 -- unknown option falls back to the usage
RC="$(usage_of -z)"
grep -q "Usage: .*indi_nexdome \[options\]" "$TMP/out" || fail "3: usage missing"
[ "$RC" -eq 1 ] || fail "3: expected exit 1, got $RC"
ok "3: unknown option prints the usage and exits 1"

props() { printf '%s\n' "$1" | timeout 20 "$BIN" 2>"$TMP/err"; }

# 4 -- the INDI protocol handshake declares the NexDome device
props "<getProperties version='1.7'/>" >"$TMP/gp"
grep -q "device='NexDome'"   "$TMP/gp" || fail "4: device 'NexDome' not declared"
grep -q "<defSwitchVector"   "$TMP/gp" || fail "4: no property vectors defined"
ok "4: <getProperties/> handshake declares the NexDome device"

# 5 -- driver identity/version reported in DRIVER_INFO
grep -q "name='DRIVER_NAME'"    "$TMP/gp" || fail "5: DRIVER_NAME missing"
grep -q "name='DRIVER_EXEC'"    "$TMP/gp" || fail "5: DRIVER_EXEC missing"
grep -A4 "name='DRIVER_NAME'" "$TMP/gp" | grep -q "NexDome"          || fail "5: DRIVER_NAME != NexDome"
grep -A4 "name='DRIVER_EXEC'" "$TMP/gp" | grep -q "indi_nexdome"     || fail "5: DRIVER_EXEC != indi_nexdome"
grep -A4 "name='DRIVER_VERSION'" "$TMP/gp" | grep -q "1.6"           || fail "5: DRIVER_VERSION != 1.6"
ok "5: DRIVER_INFO = NexDome / indi_nexdome / 1.6"

# 6 -- the CONNECTION vector is declared with its two switches
grep -q "name='CONNECTION'" "$TMP/gp" || fail "6: CONNECTION vector missing"
grep -q "name='CONNECT'"    "$TMP/gp" || fail "6: CONNECT switch missing"
grep -q "name='DISCONNECT'" "$TMP/gp" || fail "6: DISCONNECT switch missing"
ok "6: CONNECTION vector defines CONNECT/DISCONNECT"

# 7 -- a CONNECT request is answered (Alert: no NexDome hardware attached)
{
    printf "<getProperties version='1.7'/>\n"
    sleep 1
    printf "<newSwitchVector device='NexDome' name='CONNECTION'><oneSwitch name='CONNECT'>On</oneSwitch></newSwitchVector>\n"
    sleep 3
} | timeout 30 "$BIN" >"$TMP/conn" 2>"$TMP/err2"
grep -q "<setSwitchVector" "$TMP/conn" || fail "7: no setSwitchVector answer to CONNECT"
awk "/<setSwitchVector/{c=1} c&&/name='CONNECTION'/{f=1} c&&/state='/{print; exit}" "$TMP/conn" >"$TMP/connstate"
grep -q "state='Alert'" "$TMP/connstate" \
    || fail "7: CONNECT did not report the (expected) connection failure"
ok "7: CONNECT is answered with CONNECTION state=Alert (no hardware)"

echo "PASS: test.sh $PASS/7"
