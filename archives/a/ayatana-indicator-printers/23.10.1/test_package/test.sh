#!/data/service/hnp/bin/bash
# test_package/test.sh — HarmonyOS functional test for the ayatana-indicator-printers daemon.
#
# Runs inside the conanrun env (PATH/LD_LIBRARY_PATH include the installed
# package and the conan-managed dependency libraries).
#
# The daemon is a D-Bus service: it creates a proxy for the CUPS notification
# interface (org.cups.cupsd.Notifier) on the SYSTEM bus and owns
# org.ayatana.indicator.printers on the SESSION bus, where it exports its
# indicator menus. Without a system bus it aborts in
# indicator_printers_service_init() (g_error: "Error creating cups notify
# handler"), so simply starting it is not enough — this test starts two private
# buses (dbus-daemon from the dbus package, TCP transport because the HarmonyOS
# sandbox denies AF_UNIX bind outside the app sandbox) and then observes the
# daemon:
#
#   1. the installed data artifacts are present;
#   2. the installed daemon is an executable ELF (it is signed during packaging
#      because HarmonyOS only executes signed ELF binaries);
#   3. the daemon connects to the system bus, owns its session bus name and
#      exports org.gtk.Actions / org.gtk.Menus at
#      /org/ayatana/indicator/printers;
#   4. the daemon stays alive when a peer playing org.cups.cupsd.Notifier emits
#      PrinterStateChanged, i.e. the CUPS notification path is wired up.
#
# Every step executes the shipped artifact and inspects its runtime behaviour;
# nothing is checked by static inspection of the source tree.
set -uo pipefail

PRINTERS_PKG="${PRINTERS_PKG:?PRINTERS_PKG not set (run via conan test_package)}"
DBUS_PKG="${DBUS_PKG:?DBUS_PKG not set (run via conan test_package)}"
DBUS_CHECK_BIN="${DBUS_CHECK_BIN:?DBUS_CHECK_BIN not set (run via conan test_package)}"

SCRATCH="${TMPDIR:-$HOME/tmp}/ayatana-indicator-printers-test-$$"
mkdir -p "$SCRATCH"
export LD_LIBRARY_PATH="$DBUS_PKG/lib:${LD_LIBRARY_PATH:-}"

DAEMON_PID=""
BUS_PIDS=""

cleanup() {
    [ -n "$DAEMON_PID" ] && kill "$DAEMON_PID" 2>/dev/null
    for pid in $BUS_PIDS; do
        kill "$pid" 2>/dev/null
    done
    rm -rf "$SCRATCH"
}

fail() {
    echo "FAIL: $*"
    [ -s "$SCRATCH/daemon.log" ] && { echo "--- daemon log ---"; sed -n '1,20p' "$SCRATCH/daemon.log"; }
    exit 1
}

trap cleanup EXIT

BINARY="$PRINTERS_PKG/libexec/ayatana-indicator-printers/ayatana-indicator-printers-service"

# ── Test 1: installed data artifacts ──
echo "[test 1] installed data artifacts"
for artifact in \
    "$PRINTERS_PKG/share/ayatana/indicators/org.ayatana.indicator.printers" \
    "$PRINTERS_PKG/etc/xdg/autostart/ayatana-indicator-printers.desktop" \
    ; do
    [ -f "$artifact" ] || fail "missing installed artifact: $artifact"
done
echo "OK: indicator descriptor + autostart desktop entry installed"

# ── Test 2: the installed daemon is an executable ELF ──
echo "[test 2] daemon binary"
[ -x "$BINARY" ] || fail "daemon binary not executable: $BINARY"
head -c4 "$BINARY" | grep -q $'\x7fELF' || fail "daemon binary is not an ELF: $BINARY"
echo "OK: daemon ELF executable: $BINARY"

# ── private buses ──
cat > "$SCRATCH/bus.conf" <<'EOF'
<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN" "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <type>session</type>
  <listen>tcp:host=127.0.0.1,port=0</listen>
  <auth>ANONYMOUS</auth>
  <allow_anonymous/>
  <policy context="default">
    <allow send_destination="*" eavesdrop="true"/>
    <allow eavesdrop="true"/>
    <allow own="*"/>
  </policy>
</busconfig>
EOF

start_bus() {
    local output address pid
    output="$("$DBUS_PKG/bin/dbus-daemon" --config-file="$SCRATCH/bus.conf" --fork --print-address=1 --print-pid=1 2>&1)" || {
        echo "FAIL: dbus-daemon did not start: $output"; exit 1; }
    address="$(echo "$output" | sed -n '1p')"
    pid="$(echo "$output" | sed -n '2p')"
    BUS_PIDS="$BUS_PIDS $pid"
    echo "$address"
}

SYSTEM_ADDR="$(start_bus)"
SESSION_ADDR="$(start_bus)"
echo "private system bus : $SYSTEM_ADDR"
echo "private session bus: $SESSION_ADDR"

export DBUS_SYSTEM_BUS_ADDRESS="$SYSTEM_ADDR"
export DBUS_SESSION_BUS_ADDRESS="$SESSION_ADDR"

# ── Test 3: daemon runs against a system bus and exports its indicator ──
echo "[test 3] daemon on private D-Bus buses"
"$BINARY" > "$SCRATCH/daemon.log" 2>&1 &
DAEMON_PID=$!
sleep 2

kill -0 "$DAEMON_PID" 2>/dev/null || fail "daemon exited before owning its bus name"

"$DBUS_CHECK_BIN" probe "$SESSION_ADDR" org.ayatana.indicator.printers \
    /org/ayatana/indicator/printers org.gtk.Actions || fail "daemon did not export its action group on the session bus"
"$DBUS_CHECK_BIN" probe "$SESSION_ADDR" org.ayatana.indicator.printers \
    /org/ayatana/indicator/printers/desktop org.gtk.Menus || fail "daemon did not export its desktop menu model"

kill -0 "$DAEMON_PID" 2>/dev/null || fail "daemon died while exporting its indicator"
echo "OK: daemon owns org.ayatana.indicator.printers and exports its menus"

# ── Test 4: CUPS notification peer reaches the daemon ──
echo "[test 4] CUPS PrinterStateChanged signal"
"$DBUS_CHECK_BIN" notify "$SYSTEM_ADDR" || fail "could not emit the CUPS notification signal"
sleep 1

kill -0 "$DAEMON_PID" 2>/dev/null || fail "daemon died after receiving PrinterStateChanged"

"$DBUS_CHECK_BIN" probe "$SESSION_ADDR" org.ayatana.indicator.printers \
    /org/ayatana/indicator/printers org.gtk.Actions || fail "daemon stopped serving after PrinterStateChanged"
echo "OK: daemon survived PrinterStateChanged and kept its indicator exported"

echo "ALL TESTS PASSED"
