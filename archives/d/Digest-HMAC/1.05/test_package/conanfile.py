#!/usr/bin/env python3
"""Conan test_package for Digest-HMAC — Perl L1 test.

Tests that the installed Digest::HMAC module can be loaded and used
with RFC 2202 test vectors for both HMAC-MD5 and HMAC-SHA1.
"""
import os

from conan import ConanFile


class DigestHmacTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Run the test script that validates RFC 2202 HMAC vectors
        test_script = os.path.join(os.path.dirname(__file__), "test.sh")
        self.run(f"sh {test_script}", env="conanrun")
