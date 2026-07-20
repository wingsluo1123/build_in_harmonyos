#!/bin/sh
# Test script for i686-elf-grub
# Verifies grub-mkimage is available and reports its version
set -euo pipefail
grub-mkimage --version
