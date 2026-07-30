#!/bin/bash
set -e
PREFIX="${DEFAULT_PREFIX:-/storage/Users/currentUser/usr/local}"
echo "==> gtkspell3 smoke test under $PREFIX"

SO=$(find "$PREFIX/lib" -name 'libgtkspell3-3.so*' 2>/dev/null | head -1)
if [ -z "$SO" ]; then
  echo "ERROR: libgtkspell3-3.so not found under $PREFIX/lib"
  find "$PREFIX" -name '*gtkspell*' 2>/dev/null | head -50 || true
  exit 1
fi
echo "OK: found $SO"
file "$SO" || true

export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
if pkg-config --exists gtkspell3-3.0; then
  echo "OK: pkg-config gtkspell3-3.0 => $(pkg-config --modversion gtkspell3-3.0)"
  pkg-config --cflags --libs gtkspell3-3.0 || true
else
  echo "WARN: pkg-config gtkspell3-3.0 not found"
  find "$PREFIX" -name 'gtkspell3*.pc' 2>/dev/null || true
fi

echo "==> gtkspell3 test passed"
