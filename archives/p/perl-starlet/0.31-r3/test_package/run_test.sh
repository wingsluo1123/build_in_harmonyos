#!/bin/sh
# test_package/run_test.sh — Test runner for perl-starlet
# Usage: run_test.sh <perl_lib_path>
#
# Sets PERL5LIB and runs the Perl test suite.
set -e

PERL_LIB="$1"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Set PERL5LIB so Perl can find the module
if [ -n "${PERL5LIB:-}" ]; then
    export PERL5LIB="${PERL_LIB}:${PERL5LIB}"
else
    export PERL5LIB="${PERL_LIB}"
fi

# Run the Perl test suite
perl "${SCRIPT_DIR}/test_starlet.pl"
