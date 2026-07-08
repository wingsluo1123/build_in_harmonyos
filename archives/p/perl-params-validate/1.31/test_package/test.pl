#!/usr/bin/env perl
use strict;
use warnings;
use Params::Validate;

# Test: Module loaded successfully with correct version
print "Params::Validate version: $Params::Validate::VERSION\n";
if ($Params::Validate::VERSION eq '1.31') {
    print "TEST OK\n";
} else {
    print "TEST FAIL: expected 1.31, got $Params::Validate::VERSION\n";
    exit 1;
}
