#!/usr/bin/env perl
use strict;
use warnings;
use MIME::Base32 qw(encode_base32 decode_base32 encode_base32hex decode_base32hex);

# Test 1: module loads and has correct version
my $version = $MIME::Base32::VERSION;
die "ERROR: version mismatch (got '$version', expected '1.303')\n" unless $version eq '1.303';
print "ok 1 - MIME::Base32 version: $version\n";

# Test 2: encode_base32 round-trip
my $original = "hello";
my $encoded = encode_base32($original);
my $decoded = decode_base32($encoded);
die "ERROR: encode/decode round-trip failed: got '$decoded', expected '$original'\n"
    unless $decoded eq $original;
print "ok 2 - encode_base32('hello') = '$encoded'\n";

# Test 3: decode known value
my $known_enc = "NBSWY3DP";
my $known_dec = decode_base32($known_enc);
die "ERROR: decode_base32('NBSWY3DP') = '$known_dec', expected 'hello'\n"
    unless $known_dec eq "hello";
print "ok 3 - decode_base32('NBSWY3DP') = '$known_dec'\n";

# Test 4: base32hex round-trip
my $hex_enc = encode_base32hex("hello");
my $hex_dec = decode_base32hex($hex_enc);
die "ERROR: base32hex round-trip failed\n" unless $hex_dec eq "hello";
print "ok 4 - encode_base32hex('hello') = '$hex_enc'\n";

# Test 5: binary data round-trip
my $binary = pack("C*", 0..255);
my $bin_enc = encode_base32($binary);
my $bin_dec = decode_base32($bin_enc);
die "ERROR: binary round-trip failed\n" unless $bin_dec eq $binary;
print "ok 5 - binary data (0..255) round-trip OK\n";

print "\nAll tests passed.\n";
