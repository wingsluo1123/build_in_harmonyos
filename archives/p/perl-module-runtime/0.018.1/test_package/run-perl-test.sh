#!/bin/sh
set -eu
test "$#" -eq 2
exec "$1" "$2"
