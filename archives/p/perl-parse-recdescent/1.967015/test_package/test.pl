#!/usr/bin/env perl
use strict;
use warnings;
use Parse::RecDescent;

# L1 smoke test: verify module loads and parser works
my $pass = 0;
my $total = 0;

# Test 1: module loads
$total++; $pass++ if defined $Parse::RecDescent::VERSION;

# Test 2: version is correct
$total++; $pass++ if $Parse::RecDescent::VERSION eq '1.967015';

# Test 3: create a simple parser from grammar
my $grammar = q{
    expr: term '+' expr { $item[1] + $item[3] } | term
    term: /\d+/ { $item[1] }
};
my $parser = Parse::RecDescent->new($grammar);
$total++; $pass++ if defined $parser;

# Test 4: parse a simple expression
my $result = $parser->expr('42');
$total++; $pass++ if defined $result && $result == 42;

# Test 5: parse an addition expression
$result = $parser->expr('3 + 4');
$total++; $pass++ if defined $result && $result == 7;

# Test 6: parse a larger expression
$result = $parser->expr('10 + 20');
$total++; $pass++ if defined $result && $result == 30;

print "test perl-parse-recdescent 1.967015: $pass/$total OK\n";
die "FAILED: $pass/$total tests passed\n" if $pass != $total;
