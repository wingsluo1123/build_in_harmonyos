#!/bin/sh
# uget consumer test — headless behaviour of the packaged binaries.
# Usage: test.sh <uget-gtk-binary> <uget-gtk-1to2-binary>
# Both entry points handle --version/--help (and the 1to2 no-arg banner)
# before gtk_init(), so the assertions are display-free.
# Prints HMBS_TEST_PACKAGE_RESULT=<json> on completion.
set -eu

BIN_GTK="${1:-}"
BIN_1TO2="${2:-}"

if [ -z "$BIN_GTK" ] || [ -z "$BIN_1TO2" ]; then
    echo "usage: test.sh <uget-gtk-binary> <uget-gtk-1to2-binary>" >&2
    exit 2
fi

# 1. uget-gtk --version prints the banner and exits 0 (pre-gtk_init).
out="$("$BIN_GTK" --version)"
case "$out" in
    *"uGet 2.2.3"*) ;;
    *) echo "uget-gtk --version output mismatch: $out" >&2; exit 1 ;;
esac

# 2. uget-gtk --help exits 0 with the option list (pre-gtk_init).
out="$("$BIN_GTK" --help)"
case "$out" in
    *--quiet*) ;;
    *) echo "uget-gtk --help output missing options: $out" >&2; exit 1 ;;
esac

# 3. uget-gtk-1to2 without args prints the conversion banner and exits 0.
out="$("$BIN_1TO2")"
case "$out" in
    *1.10.x*) ;;
    *) echo "uget-gtk-1to2 banner mismatch: $out" >&2; exit 1 ;;
esac

echo 'HMBS_TEST_PACKAGE_RESULT={"tool": "uget", "version": "2.2.3", "consumer_cases": 3, "passed": 3, "failed": 0}'
