#!/bin/sh
set -eu
printf '[consumer] VeraCrypt version\n'
version=$(veracrypt --version)
printf '%s\n' "$version"
case "$version" in
    *"1.26.24"*) ;;
    *) printf '[consumer] unexpected VeraCrypt version\n' >&2; exit 1 ;;
esac
printf '[consumer] upstream self-test\n'
veracrypt --text --test >/dev/null 2>&1 || { printf '[consumer] upstream self-test failed\n' >&2; exit 1; }
printf '[consumer] upstream self-test passed\n'
