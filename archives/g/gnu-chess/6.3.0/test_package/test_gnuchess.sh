#!/bin/sh
set -eu

"$1" --version
"$1" --help >/dev/null
