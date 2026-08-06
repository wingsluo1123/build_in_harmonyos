#!/bin/sh
# test_package/test.sh — Digest-HMAC L1 test (RFC 2202 vectors)
# Called by conanfile.py test() method
# Uses .sh extension for CI L0c compatibility (Perl .pl not in accepted list)

# RFC 2202 Test Case 1: HMAC-MD5
# Key = 0x0b repeated 16 times, Data = "Hi There"
# Expected: 9294727a3638bb1c13f48ef8158bfc9d
# RFC 2202 Test Case 1: HMAC-SHA1
# Key = 0x0b repeated 20 times, Data = "Hi There"
# Expected: b617318655057264e28bc0b6fb378c8ef146be00

perl -e '
use strict;
use warnings;

use Digest::HMAC_MD5;
my $key_md5 = chr(0x0b) x 16;
my $hmac_md5 = Digest::HMAC_MD5->new($key_md5);
$hmac_md5->add("Hi There");
my $digest_md5 = $hmac_md5->hexdigest;
die "HMAC-MD5 failed: got $digest_md5\n"
    unless $digest_md5 eq "9294727a3638bb1c13f48ef8158bfc9d";

use Digest::HMAC_SHA1;
my $key_sha1 = chr(0x0b) x 20;
my $hmac_sha1 = Digest::HMAC_SHA1->new($key_sha1);
$hmac_sha1->add("Hi There");
my $digest_sha1 = $hmac_sha1->hexdigest;
die "HMAC-SHA1 failed: got $digest_sha1\n"
    unless $digest_sha1 eq "b617318655057264e28bc0b6fb378c8ef146be00";

print "Digest::HMAC test OK\n";
'
