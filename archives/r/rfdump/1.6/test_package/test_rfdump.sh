#!/bin/sh
# Consumer assertions for the packaged rfdump 1.6 executable (HarmonyOS PC).
#
# Every assertion runs the installed binary.  HarmonyOS PC has no X11/Wayland,
# but the ohpcd gtk/3.24.43 package is built with only the **Broadway** HTML5
# backend, so a GTK3 display connection can be established headlessly by
# starting broadwayd and pointing GDK at it.  The binary's --probe-reader entry
# point (added by patches/0006) then drives the three code paths that matter
# here without ever realising a window:
#   * the packaged GtkBuilder resource  (relocatable <prefix>/share/rfdump)
#   * the expat driven tag-type table   (rfd_types.xml)
#   * the termios serial bring-up       (/dev/ttyUSB0 does not exist here,
#                                       and neither does /var/lock)
#
# usage: test_rfdump.sh <rfdump-binary> <result-file> <work-dir>
set -u

BIN=$1
RESULT=$2
WORK=$3
DISPLAY_NUM=${RFDUMP_TEST_BROADWAY_DISPLAY:-:7}

PASSED=0
FAILED=0

pass() { PASSED=$((PASSED + 1)); echo "  [PASS] $1"; }
fail() { FAILED=$((FAILED + 1)); echo "  [FAIL] $1"; }
grepfile() { grep -F -q -- "$1" "$2" 2>/dev/null; }
check_has() { if grepfile "$2" "$3"; then pass "$1"; else fail "$1 (expected: $2)"; fi; }
check_has_not() { if grepfile "$2" "$3"; then fail "$1 (unexpected: $2)"; else pass "$1"; fi; }
check_rc() { if [ "$2" -eq "$3" ]; then pass "$1"; else fail "$1 (rc=$2, expected $3)"; fi; }
check_rcnz() { if [ "$2" -ne 0 ]; then pass "$1"; else fail "$1 (rc=0)"; fi; }

rm -rf "$WORK"
mkdir -p "$WORK/home"
HOME="$WORK/home"
XDG_CONFIG_HOME="$WORK/home/.config"
export HOME XDG_CONFIG_HOME

echo "== rfdump consumer test =="
echo "binary : $BIN"
echo "work   : $WORK"

# ── A1: the packaged executable ────────────────────────────────────────────
if [ -x "$BIN" ]; then
  pass "packaged binary is present and executable"
else
  fail "packaged binary is missing or not executable: $BIN"
fi

# ── A2-A3: headless CLI contract, no display server involved ───────────────
"$BIN" --version >"$WORK/version.out" 2>"$WORK/version.err"
check_rc "rfdump --version exits 0 without a display server" "$?" 0
check_has "rfdump --version reports the upstream version" "rfdump 1.6" "$WORK/version.out"

"$BIN" --help >"$WORK/help.out" 2>&1
check_rc "rfdump --help exits 0 without a display server" "$?" 0
check_has "rfdump --help prints the upstream usage line" "usage: rfdump" "$WORK/help.out"
check_has "rfdump --help documents the headless reader probe" "--probe-reader" "$WORK/help.out"

# ── A4: negative control - a GUI launch without a display fails closed ─────
GDK_BACKEND=broadway "$BIN" -p /dev/ttyUSB0 >"$WORK/nodisplay.out" 2>&1 &
NOD_PID=$!
n=0
while [ "$n" -lt 8 ]; do
  if ! kill -0 "$NOD_PID" 2>/dev/null; then break; fi
  sleep 1
  n=$((n + 1))
done
if kill -0 "$NOD_PID" 2>/dev/null; then
  kill -TERM "$NOD_PID" 2>/dev/null
  fail "GUI launch without a display server did not fail closed"
else
  wait "$NOD_PID" 2>/dev/null
  check_rcnz "GUI launch without a display server fails closed" "$?"
fi

# ── A5: reader probe under the Broadway display server ────────────────────
BROADWAYD=$(command -v broadwayd 2>/dev/null)
if [ -z "$BROADWAYD" ]; then
  fail "broadwayd (packaged GTK broadway display server) not found on PATH"
  PROBE_RC=-1
else
  echo "broadwayd: $BROADWAYD"
  "$BROADWAYD" "$DISPLAY_NUM" >"$WORK/broadwayd.log" 2>&1 &
  BD_PID=$!
  n=0
  while [ "$n" -lt 10 ]; do
    if grepfile "Listening on" "$WORK/broadwayd.log"; then break; fi
    if ! kill -0 "$BD_PID" 2>/dev/null; then break; fi
    sleep 1
    n=$((n + 1))
  done
  if grepfile "Listening on" "$WORK/broadwayd.log"; then
    pass "broadwayd display server reached the listening state"
  else
    fail "broadwayd did not start: $(head -1 "$WORK/broadwayd.log" 2>/dev/null)"
  fi

  GDK_BACKEND=broadway BROADWAY_DISPLAY="$DISPLAY_NUM" \
    "$BIN" --probe-reader -p /dev/ttyUSB0 >"$WORK/probe.out" 2>"$WORK/probe.err"
  PROBE_RC=$?

  echo "---- reader probe stdout ----"
  cat "$WORK/probe.out" 2>/dev/null
  echo "---- reader probe stderr ----"
  cat "$WORK/probe.err" 2>/dev/null
  echo "-----------------------------"

  check_has "GTK3 display connection established on the broadway backend" \
            "PROBE ui=OK" "$WORK/probe.out"
  check_has "5/5 GtkBuilder widgets resolved from the packaged .ui" \
            "widgets=5/5" "$WORK/probe.out"
  check_has "GtkBuilder resource loaded from the relocatable package" \
            "share/rfdump/rfdump.ui" "$WORK/probe.out"
  check_has "expat tag-type table parsed from the package" \
            "PROBE tagtypes=" "$WORK/probe.out"
  if grepfile "PROBE tagtypes=0" "$WORK/probe.out"; then
    fail "tag-type table is empty (rfd_types.xml read produced 0 entries)"
  else
    pass "tag-type table is non-empty"
  fi
  check_has "termios bring-up reached the serial device open" \
            "using serial device /dev/ttyUSB0 9600 baud" "$WORK/probe.err"
  check_has "missing /dev/ttyUSB0 is reported, not crashed on" \
            "Unable to connect to card reader device at /dev/ttyUSB0" "$WORK/probe.err"
  check_has "the report carries the OS errno text" \
            "No such file or directory" "$WORK/probe.err"
  check_has_not "no lockfile failure (HarmonyOS has no /var/lock)" \
            "Could not create lockfile" "$WORK/probe.err"
  check_has "no serial device node present, reported explicitly" \
            "PROBE device_node=MISSING" "$WORK/probe.out"
  check_rc "probe reports the documented 'no serial device node' status" "$PROBE_RC" 5

  kill -TERM "$BD_PID" 2>/dev/null
  wait "$BD_PID" 2>/dev/null
fi

TOTAL=$((PASSED + FAILED))
echo "discovered $TOTAL" >"$RESULT"
echo "passed $PASSED" >>"$RESULT"
echo "failed $FAILED" >>"$RESULT"
echo "== rfdump consumer assertions: $PASSED/$TOTAL passed =="

[ "$FAILED" -eq 0 ]
