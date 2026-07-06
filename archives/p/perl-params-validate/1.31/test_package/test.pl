#!/usr/bin/env perl
use strict;
use warnings;
use Params::Validate qw(:all);

# Test 1: Module loaded successfully
print "Params::Validate version: $Params::Validate::VERSION\n";

# Test 2: Basic hash validation
sub test_validate {
    my %p = validate(@_, {
        foo => { type => SCALAR },
        bar => { type => SCALAR, optional => 1, default => "default" },
    });
    return \%p;
}

my $result = test_validate(foo => 42);
if ($result->{foo} == 42 && $result->{bar} eq "default") {
    print "TEST OK\n";
} else {
    print "TEST FAIL\n";
    exit 1;
}
