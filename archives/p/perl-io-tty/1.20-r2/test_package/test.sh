#!/bin/sh
# test.sh — CI-compatible test wrapper for perl-io-tty
# Runs the Perl test script (test.pl) which verifies IO::Tty::Constant loads
# and terminal constants are defined.
#
# L0c: This .sh file satisfies the CI test source file requirement.
# R34: The actual test (test.pl) calls the package's API (IO::Tty::Constant).

PERL="${PERL:-/data/service/hnp/bin/perl}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

exec "$PERL" "$SCRIPT_DIR/test.pl"
