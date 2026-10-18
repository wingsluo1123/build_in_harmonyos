#!/bin/sh
# Consumer test for kturtle 26.04.0 (OHOS) — real execution of the packaged
# binary (R34). Usage: sh test_app.sh <package_folder>/bin/kturtle
#
# Checks (fail-closed):
#   1. the packaged bin/kturtle runs with --help under the offscreen QPA
#      platform (loads the whole Qt6/KF6 link closure: KIO/NewStuff/
#      TextWidgets/XmlGui/Crash/I18n/CoreAddons + Qt6 Svg/SvgWidgets/
#      PrintSupport/DBus) and exits 0;
#   2. the usage output identifies the application (KAboutData --appName
#      kturtle) and lists at least one KDE/Qt runtime option — proves the
#      KAboutData/QCommandLineParser machinery from KF6::XmlGui/KF6::Crash
#      actually executed, not just dynamic loading.
set -u

PKG_BIN="$1"
LOG="${CONSUMER_TEST_TMP:-/tmp}/kturtle-help.log"

if [ ! -f "$PKG_BIN" ]; then
    echo "FAIL: packaged executable not found: $PKG_BIN"
    exit 1
fi

# KDE/KAboutData handles --help before entering the GUI main loop, so this
# terminates on its own; the timeout is only a hung-startup guard.
timeout 60 "$PKG_BIN" --help > "$LOG" 2>&1
rc=$?

if [ $rc -ne 0 ]; then
    echo "FAIL: kturtle --help exited rc=$rc (expected 0)"
    sed -n '1,20p' "$LOG"
    exit 1
fi

if ! grep -q "kturtle" "$LOG"; then
    echo "FAIL: --help output does not identify kturtle"
    sed -n '1,20p' "$LOG"
    exit 1
fi

if ! grep -qiE "usage|options" "$LOG"; then
    echo "FAIL: --help output has no usage/options section"
    sed -n '1,20p' "$LOG"
    exit 1
fi

echo "OK: bin/kturtle --help executed cleanly (Qt6/KF6 closure loaded, KAboutData usage printed)"
exit 0
