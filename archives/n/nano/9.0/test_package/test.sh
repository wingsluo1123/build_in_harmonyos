#!/usr/bin/env sh
set -eu

version_output=$(nano --version)
case "$version_output" in
    *"version 9.0"*) ;;
    *)
        printf '%s\n' "$version_output" >&2
        exit 1
        ;;
esac
