#!/bin/sh
set -eu

# 1) Hardware independent CLI check: the MCU table must be printed.
set +e
output=$(teensy_loader_cli --list-mcus 2>&1)
status=$?
set -e

test "$status" -eq 1
printf '%s\n' "$output" | grep -q "Supported MCUs are:"
printf '%s\n' "$output" | grep -q "atmega32u4"
printf '%s\n' "$output" | grep -q "at90usb1286"

# 2) Real USB backend check: -b (boot only) skips the firmware file and calls
#    teensy_open(), which runs libusb_init() and enumerates the USB bus.
#    Without a Teensy attached the tool must fail loudly, never silently
#    report success.
set +e
usb_output=$(teensy_loader_cli --mcu=atmega32u4 -b 2>&1)
usb_status=$?
set -e

if [ "$usb_status" -ne 0 ]; then
    printf '%s\n' "$usb_output" | grep -q "Unable to open device"
fi
