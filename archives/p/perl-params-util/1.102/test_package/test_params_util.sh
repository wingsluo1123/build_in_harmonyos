#!/bin/sh
# test_params_util.sh — L1 test for perl-params-util (Params::Util)
# Tests that the installed module files exist and core functions work
# in pure Perl fallback mode (PERL_PARAMS_UTIL_PP=1).
set -eu

PKG_FOLDER="${1:?Usage: test_params_util.sh <pkg_folder>}"

SITE_ARCH="$PKG_FOLDER/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux"

# Check expected files exist
for f in \
    "$SITE_ARCH/Params/Util.pm" \
    "$SITE_ARCH/Params/Util/PP.pm" \
    "$SITE_ARCH/auto/Params/Util/Util.so"; do
    if [ ! -f "$f" ]; then
        echo "FAIL: Expected file not found: $f" >&2
        exit 1
    fi
    echo "Found: $f"
done

# Test module loading and core functions (pure Perl fallback)
export PERL5LIB="$SITE_ARCH"
export PERL_PARAMS_UTIL_PP=1

perl -e '
use Params::Util;
my $v = $Params::Util::VERSION;
print "version: $v\n";
my $s = defined Params::Util::_STRING("hello") ? "pass" : "fail";
print "_STRING: $s\n";
my $n = defined Params::Util::_NUMBER(42) ? "pass" : "fail";
print "_NUMBER: $n\n";
die "_STRING test failed" unless $s eq "pass";
die "_NUMBER test failed" unless $n eq "pass";
'

echo "ALL TESTS PASSED"
