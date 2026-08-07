#!/usr/bin/env python3
"""Conan test_package — Digest::SHA3 Perl XS module.

L1 test: Verify the Perl module .so exists in the package and call actual
SHA-3 API functions (sha3_256_hex) to validate functionality.

On OHOS with HMDFS, .so loading may be blocked by SELinux context (E073).
The test script (test_sha3.sh) handles this internally:
  - Verifies .so and .pm file presence (always)
  - Attempts to load module and call sha3_256_hex with known test vectors
  - If "Permission denied" (HMDFS SELinux): exits 0 after verifying package contents
  - Any other load failure: exits 1 (real test failure, not silently swallowed)
"""
import os

from conan import ConanFile


class PerlDigestSHA3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["perl-digest-sha3"].package_folder
        perl_lib = os.path.join(pkg_folder, "lib", "perl5")
        test_script = os.path.join(os.path.dirname(__file__), "test_sha3.sh")

        # R34: Run test script that calls actual SHA-3 API (sha3_256_hex, sha3_512_hex)
        # The script verifies .so/.pm presence, loads the module, and calls SHA-3 functions.
        # On OHOS HMDFS, "Permission denied" (E073) is tolerated — all other errors fail.
        self.run(f'sh "{test_script}" "{perl_lib}"', env="conanrun")
        self.output.info("Digest::SHA3 test passed (module verified or platform limitation acknowledged)")
