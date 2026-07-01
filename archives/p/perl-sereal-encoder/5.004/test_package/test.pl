#!/usr/bin/env perl
# test_package test for perl-sereal-encoder
use strict;
use warnings;
use Sereal::Encoder;

my $encoder = Sereal::Encoder->new();
my $data = { foo => 'bar', baz => [1, 2, 3] };
my $encoded = $encoder->encode($data);
print "Sereal::Encoder version: ", Sereal::Encoder->VERSION, "\n";
print "Encoded data length: ", length($encoded), "\n";
print "test perl-sereal-encoder 5.004: OK\n";
