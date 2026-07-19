#!/bin/sh
set -eu

dfu-util --version 2>&1 | grep -q "dfu-util 0.11"
dfu-prefix --version 2>&1 | grep -q "dfu-prefix 0.11"
dfu-suffix --version 2>&1 | grep -q "dfu-suffix 0.11"
