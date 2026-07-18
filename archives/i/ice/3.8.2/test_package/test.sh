#!/bin/sh
set -eu

# Verify icebox --version outputs the expected version string
version_output="$(icebox --version 2>&1)"
case "$version_output" in
  *3.8.2*) ;;
  *) echo "FAIL: icebox --version expected '3.8.2', got: $version_output"; exit 1 ;;
esac

slice2cpp "$1"
test -f Test.cpp
test -f Test.h
