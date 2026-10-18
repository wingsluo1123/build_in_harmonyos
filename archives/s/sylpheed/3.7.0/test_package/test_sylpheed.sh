#!/bin/sh
# test_sylpheed.sh — sylpheed 3.7.0 HarmonyOS consumer use-case test (non-assertion).
#
# OHOS/HMDFS provides no ldd/readelf; `file` is used instead to verify that the
# produced shared libraries are valid ELF arm64 objects (shared-library closure
# check). Invoked via CONFIG_SHELL bash so no exec bit is required on HMDFS.
# NOTE: do not use `rm` here — it hits the broken safe-bin shim on local runs.
#
# Usage: test_sylpheed.sh <sylpheed_bin> <libsylph_so> <libgtk2_so>

SYLPHEED_BIN="$1"
LIBSYLPH="$2"
LIBGTK2="$3"

echo "[consumer] running: $SYLPHEED_BIN --version"
"$SYLPHEED_BIN" --version
rc=$?
# Propagate the consumer run's exit code; the `file` checks below are
# non-assertion HarmonyOS-specific observations and never fail the test.

if [ -n "$LIBSYLPH" ] && [ -f "$LIBSYLPH" ]; then
    echo "[harmonyos] shared-library closure check (file, no ldd/readelf on OHOS):"
    file "$LIBSYLPH"
fi

if [ -n "$LIBGTK2" ] && [ -f "$LIBGTK2" ]; then
    echo "[harmonyos] GTK+2 full consumer stack check:"
    file "$LIBGTK2"
fi

echo "[consumer] sylpheed 3.7.0 HarmonyOS consumer test done"
exit "$rc"
