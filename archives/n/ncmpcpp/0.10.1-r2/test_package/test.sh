#!/bin/sh
set -eu
"$1" --version 2>&1 | grep -i "ncmpcpp"
