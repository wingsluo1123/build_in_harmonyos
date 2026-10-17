#!/bin/bash
# Smoke test for the xdg-desktop-portal package deliverables.
# This file satisfies CI L0c (test source file in test_package/); the real
# assertions run in conanfile.py test() (daemon --version, pc file,
# interfaces_dir resolution, interface XMLs, D-Bus service file).
# Layout note: conan's MesonToolchain maps libexecdir to bin/; the dataonly
# pc is installed to share/pkgconfig/ (both verified on the real package).
set -euo pipefail

PKG_DIR="${1:?usage: test_smoke.sh <package_folder>}"

DAEMON="$PKG_DIR/bin/xdg-desktop-portal"
[ -x "$DAEMON" ] || DAEMON="$PKG_DIR/libexec/xdg-desktop-portal"

PC_FILE="$PKG_DIR/share/pkgconfig/xdg-desktop-portal.pc"
[ -f "$PC_FILE" ] || PC_FILE="$PKG_DIR/lib/pkgconfig/xdg-desktop-portal.pc"

# 1. daemon binary exists
test -x "$DAEMON" || { echo "FAIL: daemon missing: $DAEMON"; exit 1; }

# 2. daemon reports the adapted version (config.h PACKAGE_STRING).
#    It links shared glib/json-glib/gdk-pixbuf from the dependency packages;
#    pass their package libdirs via optional second argument (colon list) —
#    the conanfile.py test() passes the resolved dependency libdirs.
DEP_LIBS="${2:-}"
OUT="$(LD_LIBRARY_PATH="${DEP_LIBS}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$DAEMON" --version 2>&1 || true)"
echo "daemon --version: $OUT"
case "$OUT" in
  *xdg-desktop-portal\ 1.22.1*) ;;
  *) echo "FAIL: unexpected version: $OUT"; exit 1 ;;
esac

# 3. dataonly pc file exists
test -f "$PC_FILE" || { echo "FAIL: pc missing: $PC_FILE"; exit 1; }

# 4. interfaces_dir variable points at installed XMLs (relocatable
#    ${pcfiledir}/../.. prefix, expanded against the package folder)
IFACE_DIR="$(sed -n 's/^interfaces_dir=//p' "$PC_FILE" \
  | sed "s|\${pcfiledir}/../..|$PKG_DIR|; s|\${prefix}|$PKG_DIR|; s|\${datadir}|$PKG_DIR/share|; s|\${datarootdir}|$PKG_DIR/share|")"
test -d "$IFACE_DIR" || { echo "FAIL: interfaces_dir not a dir: $IFACE_DIR"; exit 1; }
test -f "$IFACE_DIR/org.freedesktop.portal.Request.xml" \
  || { echo "FAIL: Request.xml missing"; exit 1; }

echo "All smoke tests passed"
