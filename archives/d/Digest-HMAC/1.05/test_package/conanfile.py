#!/usr/bin/env python3
"""Conan test_package for Digest-HMAC — Perl L1 test.

Tests that the installed Digest::HMAC module can be loaded and used
with RFC 2202 test vectors for both HMAC-MD5 and HMAC-SHA1.
"""
from conan import ConanFile


class DigestHmacTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test that the Perl module can be loaded and HMAC works correctly
        # RFC 2202 Test Case 1: key=0x0b*16, data="Hi There"
        test_script = (
            'use Digest::HMAC_MD5; '
            'my $key = chr(0x0b) x 16; '
            'my $hmac_md5 = Digest::HMAC_MD5->new($key); '
            '$hmac_md5->add("Hi There"); '
            'my $digest_md5 = $hmac_md5->hexdigest; '
            'die "HMAC-MD5 failed: $digest_md5" '
            'unless $digest_md5 eq "9294727a3638bb1c13f48ef8158bfc9d"; '
            'use Digest::HMAC_SHA1; '
            'my $key2 = chr(0x0b) x 20; '
            'my $hmac_sha1 = Digest::HMAC_SHA1->new($key2); '
            '$hmac_sha1->add("Hi There"); '
            'my $digest_sha1 = $hmac_sha1->hexdigest; '
            'die "HMAC-SHA1 failed: $digest_sha1" '
            'unless $digest_sha1 eq "b617318655057264e28bc0b6fb378c8ef146be00"; '
            'print "Digest::HMAC test OK\\n";'
        )
        self.run(f"perl -e '{test_script}'", env="conanrun")
