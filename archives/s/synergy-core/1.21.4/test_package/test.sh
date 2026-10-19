#!/bin/sh
set -eu

binary=${1:?synergy-core binary is required}
expected_version=${2:?expected version is required}

version_output=$("$binary" --version)
case "$version_output" in
  *"v$expected_version"*) ;;
  *)
    printf '%s\n' "unexpected synergy-core version output: $version_output" >&2
    exit 1
    ;;
esac

help_output=$("$binary" --help)
case "$help_output" in
  *coremode*) ;;
  *)
    printf '%s\n' "unexpected synergy-core help output: $help_output" >&2
    exit 1
    ;;
esac

# no-mode invocation must print usage and exit 0 (upstream showHelpText path)
usage_rc=0
usage_output=$("$binary" 2>&1) || usage_rc=$?
if [ "$usage_rc" -ne 0 ]; then
  printf '%s\n' "unexpected no-mode exit code: $usage_rc" >&2
  exit 1
fi
case "$usage_output" in
  *coremode*) ;;
  *)
    printf '%s\n' "unexpected no-mode output: $usage_output" >&2
    exit 1
    ;;
esac

printf '%s\n' "synergy-core consumer checks passed"
