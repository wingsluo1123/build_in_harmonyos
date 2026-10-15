#!/bin/sh
# Consumer end-to-end reproduction entry for the packaged kookbook 0.3.0.
#
# Kept POSIX sh (not zsh) on purpose: this script ships inside the package
# and is meant to be runnable on a minimal HarmonyOS PC target where a zsh
# binary is not guaranteed. Safe mode is still applied.
set -eu
#
# The real case (E2E-KOOKBOOK-01) lives in test_kookbook_e2e.py, which is
# what test_package/conanfile.py runs. This script documents and mirrors
# that call so the same check can be reproduced by hand on the target:
#
#   LD_LIBRARY_PATH=<dep pkg>/lib:...   (Qt6 runtime closure)
#   QT_QPA_PLATFORM=offscreen
#   HOME=<throwaway home>               (isolated settings + collection)
#   <pkg>/bin/kookbook                  (the packaged application)
#
# The collection is placed at <HOME>/Documents/recipes — the location
# upstream opens when no user collection setting is present.
#
# Exit code: 0 when the application scans and reads every recipe, non-zero else.
APP_BIN="${1:-}"
FIXTURES="${2:-$(dirname "$0")/fixtures}"
if [ $# -lt 1 ] || [ -z "$APP_BIN" ] || [ ! -x "$APP_BIN" ]; then
    echo "usage: $0 <pkg>/bin/kookbook [fixtures-dir]" >&2
    exit 2
fi
exec python3 "$(dirname "$0")/test_kookbook_e2e.py" "$APP_BIN" "$FIXTURES"
