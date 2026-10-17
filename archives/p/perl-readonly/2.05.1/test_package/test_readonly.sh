#!/system/bin/sh
set -eu
[ "$#" -eq 2 ]
exec "$1" "$2"
