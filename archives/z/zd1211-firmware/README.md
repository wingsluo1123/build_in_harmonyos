# zd1211-firmware

Firmware for ZyDAS ZD1211 USB-WLAN devices.

## Description

This package contains the firmware binary files for ZyDAS ZD1211/ZD1211B USB wireless LAN devices. The firmware is loaded by the kernel driver when the device is connected.

## Versions

- 1.5 (2026-06-25): Prebuilt firmware package

## Build System

None — this is a firmware binary package. No compilation is required. The firmware files are installed directly to `lib/firmware/`.

## Installation

Firmware files are installed to `~/usr/local/lib/firmware/`. The kernel driver will automatically load the firmware when the device is detected.
