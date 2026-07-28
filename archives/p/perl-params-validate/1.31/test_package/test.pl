#!/usr/bin/env perl
use strict;
use warnings;
use Params::Validate qw(validate validate_pos SCALAR);

# Test 1: Module loaded with correct version
print "Params::Validate version: $Params::Validate::VERSION\n";
die "TEST FAIL: expected 1.31, got $Params::Validate::VERSION\n"
    unless $Params::Validate::VERSION eq '1.31';

# Test 2: validate() with valid named params
sub valid_named {
    my %p = validate(@_, { name => { type => SCALAR }, count => { type => SCALAR } });
    return $p{name};
}
valid_named(name => 'hello', count => 42);
print "Test 2 (validate, valid params): OK\n";

# Test 3: validate() with missing required param — should fail
eval {
    valid_named(name => 'hello');  # missing 'count'
};
die "Test 3 FAIL: expected validation error for missing required param\n" unless $@;
print "Test 3 (validate, missing required): OK (correctly rejected)\n";

# Test 4: validate_pos() with valid positional params
sub valid_pos {
    validate_pos(@_, { type => SCALAR }, { type => SCALAR });
}
valid_pos('hello', 42);
print "Test 4 (validate_pos, valid): OK\n";

# Test 5: validate_pos() with wrong number of args — should fail
eval {
    valid_pos('hello');  # only 1 arg, expects 2
};
die "Test 5 FAIL: expected validation error for wrong arg count\n" unless $@;
print "Test 5 (validate_pos, wrong count): OK (correctly rejected)\n";

print "ALL TESTS PASSED\n";
