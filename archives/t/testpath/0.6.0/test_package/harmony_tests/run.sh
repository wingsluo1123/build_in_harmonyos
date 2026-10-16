#!/bin/sh
set -eu
# HARMONY_TEST_COUNT=1; same installed API consumer includes the owned Harmony case.
exec "$1" -B "$(dirname "$0")/../test.py" "$2"
