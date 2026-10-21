#!/system/bin/sh
set -eu
[ "$#" -eq 2 ] || exit 64
exec "$1" "$2"
