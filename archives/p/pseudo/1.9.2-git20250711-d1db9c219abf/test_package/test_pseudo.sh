#!/bin/sh
# Consumer-side execution of the packaged pseudo client.
set -eu

PSEUDO_BIN="$1"
PSEUDO_INSTALL_PREFIX="$2"
WORK="$(pwd)/pseudo-consumer"
STATE_ROOT="/data/storage/el2/base/cache/pseudo-consumer-$$"
cleanup() {
    rm -rf "$WORK" "$STATE_ROOT"
}
trap cleanup EXIT INT TERM
rm -rf "$WORK" "$STATE_ROOT"
mkdir -p "$WORK" "$STATE_ROOT"

version=$("$PSEUDO_BIN" -V)
case "$version" in
    *1.9.2*) ;;
    *) echo "unexpected pseudo version: $version" >&2; exit 1 ;;
esac

# PSEUDO_PREFIX is where pseudo itself is installed: the client re-executes
# $PSEUDO_PREFIX/bin/pseudo as its daemon and preloads
# $PSEUDO_PREFIX/lib/libpseudo.so from there.  Pointing it at an empty scratch
# directory makes the client abort with "exec of pseudo daemon failed", so keep
# the installed prefix and only redirect the state database.  The wrapped
# command writes into a scratch directory instead, so the package stays clean.
PSEUDO_PREFIX="$PSEUDO_INSTALL_PREFIX" \
PSEUDO_LOCALSTATEDIR="$STATE_ROOT" \
PSEUDO_DISABLED=0 \
    "$PSEUDO_BIN" /bin/sh -c 'printf consumer-ok > "$1/result"' sh "$WORK"

test "$(cat "$WORK/result")" = consumer-ok

# Exercise a second wrapped filesystem operation.  Besides proving that the
# pseudo client can rename through its daemon, this verifies the first result
PSEUDO_PREFIX="$PSEUDO_INSTALL_PREFIX" \
PSEUDO_LOCALSTATEDIR="$STATE_ROOT" \
PSEUDO_DISABLED=0 \
    "$PSEUDO_BIN" /bin/sh -c 'mv "$1/result" "$1/result.moved"' sh "$WORK"

if [ -e "$WORK/result" ] || [ "$(cat "$WORK/result.moved")" != consumer-ok ]; then
    echo "pseudo wrapped rename did not preserve the file content" >&2
    exit 1
fi
echo "pseudo consumer test: version and wrapped-command checks passed"
