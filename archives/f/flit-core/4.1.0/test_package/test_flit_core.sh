#!/bin/sh
set -eu
exec "$1" -B "$(dirname "$0")/consumer.py" "$2"
