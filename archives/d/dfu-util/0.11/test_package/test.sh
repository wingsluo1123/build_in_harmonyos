#!/bin/sh
set -eu

check_version() {
    command="$1"
    expected="$2"
    output="$("$command" --version 2>&1)"
    case "$output" in
        *"$expected"*) ;;
        *) exit 1 ;;
    esac
}

check_version dfu-util "dfu-util 0.11"
check_version dfu-prefix "dfu-prefix 0.11"
check_version dfu-suffix "dfu-suffix 0.11"
