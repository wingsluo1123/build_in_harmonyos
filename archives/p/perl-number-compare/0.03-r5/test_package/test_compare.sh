#!/bin/sh
# test_compare.sh — smoke test for perl-number-compare
# CI L0c: recognized test source file (.sh extension)
# Verifies Number::Compare module API: new(), test() with comparison operators
# PERL5LIB is set by conanrun environment (from package_info runenv_info)

perl -e '
use Number::Compare;
my $comp = Number::Compare->new(">10");
die "test failed: 15 should be >10" unless $comp->test(15);
die "test failed: 5 should not be >10" if $comp->test(5);
print "Number::Compare test: OK\n";
'
