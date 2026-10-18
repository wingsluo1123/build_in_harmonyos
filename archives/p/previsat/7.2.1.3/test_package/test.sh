#!/data/service/hnp/bin/bash
# test_package/test.sh — HarmonyOS functional test for the PreviSat application.
#
# Runs inside the conanrun env (LD_LIBRARY_PATH includes the conan-managed Qt6
# libraries). The application is a Qt6 GUI program; the HarmonyOS PC images have
# no windowing system, so it is started with the Qt "offscreen" platform plugin
# that the packaged Qt6 (qtbase-sql-dbus) provides.
#
# The test executes the installed binary and inspects real runtime effects,
# instead of only validating the packaging layout:
#   1. installed tree (binary + data/ + translations/) complete;
#   2. the binary is an executable, signed ELF (HarmonyOS only executes signed
#      ELF binaries);
#   3. the application starts headless and stays alive (the whole dependency
#      chain, including the Qt6 Sql and Multimedia modules, resolves at load
#      time);
#   4. the relocatable data layout works: the application creates its runtime
#      tree (data/config, log/, cache/, starlink/, Astropedia/) next to the
#      executable and logs the loading of its XML data files, i.e. the
#      PORTABLE_BUILD data root is used and not /usr/share/Astropedia;
#   5. the packaged Qt6 SQLite driver is usable: the application opens its
#      satellite database without a "driver not loaded" failure.
set -uo pipefail

PREVISAT_PKG="${PREVISAT_PKG:?PREVISAT_PKG not set (run via conan test_package)}"

SCRATCH="${TMPDIR:-$HOME/tmp}/previsat-test-$$"
mkdir -p "$SCRATCH"
APP_PID=""

cleanup() {
    [ -n "$APP_PID" ] && kill "$APP_PID" 2>/dev/null
}

fail() {
    echo "FAIL: $*"
    [ -s "$SCRATCH/app.out" ] && { echo "--- application output ---"; sed -n '1,25p' "$SCRATCH/app.out"; }
    exit 1
}

trap cleanup EXIT

BINARY="$PREVISAT_PKG/bin/PreviSat"

# ── Test 1: installed files ──
echo "[test 1] installed application tree"
[ -x "$BINARY" ] || fail "PreviSat binary not found/executable: $BINARY"
[ -f "$PREVISAT_PKG/bin/data/satellites.db" ] || fail "satellite database not installed"
[ -f "$PREVISAT_PKG/bin/data/sound/flare.wav" ] || fail "sound data not installed"
[ -f "$PREVISAT_PKG/bin/translations/qt_fr.qm" ] || fail "translations not installed"
echo "OK: binary + data (satellites.db, sound) + translations installed"

# ── Test 2: signed executable ELF ──
echo "[test 2] executable ELF with HarmonyOS signature"
head -c4 "$BINARY" | grep -q $'\x7fELF' || fail "PreviSat is not an ELF binary: $BINARY"
if [ -x /data/service/hnp/bin/llvm-readelf ]; then
    /data/service/hnp/bin/llvm-readelf -S "$BINARY" | grep -q "\.codesign" \
        || fail "PreviSat ELF carries no .codesign section (not signed)"
    echo "OK: ELF binary signed (.codesign present)"
fi

# ── Test 3: headless start-up (offscreen QPA plugin) ──
echo "[test 3] headless start-up with the offscreen platform plugin"
cd "$PREVISAT_PKG/bin" || fail "cannot enter the package bin directory"
rm -rf log cache starlink Astropedia
QT_QPA_PLATFORM=offscreen "$BINARY" -platform offscreen > "$SCRATCH/app.out" 2>&1 &
APP_PID=$!
sleep 12

kill -0 "$APP_PID" 2>/dev/null || fail "application exited during start-up"
grep -q "Error loading shared library\|symbol not found\|Could not load the Qt platform plugin" "$SCRATCH/app.out" \
    && fail "application failed to load its dependencies"
echo "OK: application is running headless (pid $APP_PID)"

# ── Test 4: relocatable data root next to the executable ──
echo "[test 4] portable data layout on HMDFS"
[ -d "$PREVISAT_PKG/bin/log" ] || fail "no runtime log directory created next to the executable"
LOGFILE=$(ls -t "$PREVISAT_PKG/bin/log"/*.log 2>/dev/null | head -1)
[ -n "$LOGFILE" ] || fail "application did not write a log file"
grep -q "PreviSat 7.2.1.3" "$LOGFILE" || fail "log file does not report the packaged version"
grep -q "Lecture fichier configuration.xml OK" "$LOGFILE" \
    || fail "application did not load its configuration data (log: $LOGFILE)"
[ -d "$PREVISAT_PKG/bin/data/config" ] || fail "application did not materialise its local data tree"
grep -q "n'existe pas, veuillez réinstaller" "$SCRATCH/app.out" \
    && fail "application fell back to the /usr/share data root"
echo "OK: data read from the package prefix, runtime tree created (log: $LOGFILE)"

# ── Test 5: packaged Qt SQLite driver ──
echo "[test 5] Qt SQLite driver of the packaged Qt6 Sql module"
if grep -q "QSQLITE driver not loaded\|QSqlDatabase: .* driver not loaded" "$LOGFILE" "$SCRATCH/app.out"; then
    fail "the Qt SQLite driver could not be loaded"
fi
[ -f "$PREVISAT_PKG/bin/data/satellites.db" ] || fail "satellite database disappeared during start-up"
echo "OK: satellite database opened without driver errors"

kill -0 "$APP_PID" 2>/dev/null || fail "application died before the end of the test"
echo "ALL TESTS PASSED"
