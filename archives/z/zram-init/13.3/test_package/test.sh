#!/bin/sh
# Layout + content assertions for the packaged zram-init 13.3 (POSIX sh).
# usage: test.sh <package_folder>
set -eu

PKG="$1"
fail() { echo "FAIL: $*" >&2; exit 1; }

SCRIPT="$PKG/bin/zram-init"
[ -f "$SCRIPT" ] || fail "missing $SCRIPT"

# Executable bit survived packaging (mode bits read via ls, no os.access probe
# — HMDFS normalizes modes to e.g. -rwxrwx--- (770), E046, so we assert the
# user triad only: it carries the exec bit we actually need).
ls -l "$SCRIPT" | grep -q '^[-bcl]rwx' || fail "script not executable (user bit)"

# Upstream shebang kept (recipe builds with MODIFY_SHEBANG=FALSE: reproducible,
# no build-host sh path baked into the artifact).
head -1 "$SCRIPT" | grep -q '^#!/usr/bin/env sh$' || fail "unexpected shebang"

# make ran its sed substitution: no template placeholders may remain.
grep -q '@MODIR@' "$SCRIPT" && fail "unsubstituted @MODIR@ placeholder"
grep -q '@EXENAME@' "$SCRIPT" && fail "unsubstituted @EXENAME@ placeholder"
grep -q 'Usage: ${BASENAME}' "$SCRIPT" || fail "usage message missing"

# Man page present and plausible.
[ -s "$PKG/share/man/man8/zram-init.8" ] || fail "man page missing/empty"
grep -qi 'zram' "$PKG/share/man/man8/zram-init.8" || fail "man page content wrong"

# modprobe.d module options (runtime contract: num_devices for zram devices).
[ -f "$PKG/res/modprobe.d/zram.conf" ] || fail "res/modprobe.d/zram.conf missing"
grep -q '^options zram num_devices=3' "$PKG/res/modprobe.d/zram.conf" \
    || fail "zram.conf missing upstream module options"

# zsh completion present with upstream compdef header.
COMP="$PKG/share/zsh/site-functions/_zram-init"
[ -f "$COMP" ] || fail "zsh completion missing"
grep -q '^#compdef zram-init' "$COMP" || fail "completion header wrong"

echo "test.sh: all 10 layout/content assertions passed"
