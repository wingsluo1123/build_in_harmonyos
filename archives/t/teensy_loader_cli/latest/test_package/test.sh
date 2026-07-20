#!/bin/sh
set -eu

set +e
output=$(teensy_loader_cli --list-mcus 2>&1)
status=$?
set -e

test "$status" -eq 1
printf '%s\n' "$output" | grep -q "Supported MCUs are:"
printf '%s\n' "$output" | grep -q "atmega32u4"
printf '%s\n' "$output" | grep -q "at90usb1286"
