#!/bin/sh
# Consumer smoke script for the packaged kapptemplate CLI.
# The real test() logic lives in conanfile.py (environment assembly + direct
# execution of bin/kapptemplate in its non-interactive template-generator
# mode); this file documents and mirrors the calls so the check can also be
# reproduced manually on the device:
#
#   export QT_QPA_PLATFORM=offscreen
#   export LD_LIBRARY_PATH=<dep pkg>/lib:<dep pkg>/bin:...
#   export XDG_DATA_DIRS=<pkg>/share           # templates live here
#   export TMPDIR=<writable-dir>               # /tmp is read-only on OHOS
#   <pkg>/bin/kapptemplate --version
#   <pkg>/bin/kapptemplate --list-templates
#   <pkg>/bin/kapptemplate MyApp "$TMPDIR/gen" Me me@example.org 0.1 kde-frameworks6
#
# Exit code: 0 when version/list/generation all succeed, non-zero else.
set -eu
APP_BIN="${1:-}"
if [ -z "$APP_BIN" ] || [ ! -x "$APP_BIN" ]; then
    echo "usage: $0 <path-to-kapptemplate>" >&2
    exit 2
fi
TMPDIR="${TMPDIR:-$(mktemp -d)}"
export QT_QPA_PLATFORM=offscreen

"$APP_BIN" --version
"$APP_BIN" --list-templates

GEN="$TMPDIR/kapptemplate-consumer"
mkdir -p "$GEN"
"$APP_BIN" MyApp "$GEN" "Test Author" "test@example.org" "0.1" kde-frameworks6
test -f "$GEN/myapp/CMakeLists.txt"
test -f "$GEN/myapp/src/myappview.cpp"
echo "consumer generation OK: $GEN/myapp"
