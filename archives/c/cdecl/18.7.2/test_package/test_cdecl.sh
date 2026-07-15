#!/usr/bin/env bash
set -euo pipefail

cdecl_bin="$1"

"$cdecl_bin" --version | grep -q "cdecl 18.7.2"

output=$(printf 'declare x as pointer to int\n' | "$cdecl_bin")
case "$output" in
  *"int *x;"*) ;;
  *)
    echo "unexpected declare output: $output" >&2
    exit 1
    ;;
esac

output=$(printf 'explain int *x\n' | "$cdecl_bin")
case "$output" in
  *"declare x as pointer to int"*) ;;
  *)
    echo "unexpected explain output: $output" >&2
    exit 1
    ;;
esac
