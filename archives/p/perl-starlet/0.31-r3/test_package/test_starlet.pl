#!/usr/bin/env perl
# test_package/test_starlet.pl — Functional test for Starlet Perl module
# Run via: perl -I<lib_dir> test_starlet.pl
use strict;
use warnings;

my $pass = 0;
my $fail = 0;

# Test 1: Module loads
eval { require Starlet };
if ($@) {
    print "FAIL: Cannot load Starlet: $@\n";
    $fail++;
} else {
    $pass++;
}

# Test 2: Version check
my $version = Starlet->VERSION;
if (defined $version && $version eq '0.31') {
    $pass++;
} else {
    print "FAIL: Version mismatch: got '" . ($version // 'undef') . "', expected '0.31'\n";
    $fail++;
}

# Test 3: Starlet::Server loads
eval { require Starlet::Server };
if ($@) {
    print "FAIL: Cannot load Starlet::Server: $@\n";
    $fail++;
} else {
    $pass++;
}

# Test 4: Plack::Handler::Starlet loads
eval { require Plack::Handler::Starlet };
if ($@) {
    print "FAIL: Cannot load Plack::Handler::Starlet: $@\n";
    $fail++;
} else {
    $pass++;
}

if ($fail == 0) {
    print "PASS: All $pass tests passed\n";
} else {
    print "FAIL: $fail tests failed\n";
}
exit($fail > 0 ? 1 : 0);
