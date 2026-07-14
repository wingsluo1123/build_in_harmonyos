#!/bin/sh
# test_package/test.sh — Shell wrapper for Perl functional test
# CI L0c requires a recognized test source file (.c/.cpp/.sh/.py)
# This wrapper invokes the Perl test script with proper environment.
set -e

export PERL_PARAMS_UTIL_PP=1
export PERL5LIB="/storage/Users/currentUser/usr/local/perl5/lib/perl5:\
/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/aarch64-linux:\
/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec perl "$SCRIPT_DIR/test.pl"
