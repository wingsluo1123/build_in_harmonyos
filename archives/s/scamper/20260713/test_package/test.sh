#!/bin/sh
set -eu
"$1" -v 2>&1 | grep -i "scamper"
