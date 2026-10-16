#!/bin/sh
set -eu
[ "$#" -eq 2 ]
[ -x "$1" ]
[ -f "$2" ]
exec "$1" "$2"
