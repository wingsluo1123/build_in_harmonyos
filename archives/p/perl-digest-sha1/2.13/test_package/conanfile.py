#!/usr/bin/env python3
"""Conan test_package — Digest::SHA1 Perl XS module.

L1 test: Verify the Perl module .so exists in the package and call actual
Digest::SHA1 API functions (new, add, hexdigest) to validate functionality.

On OHOS with HMDFS, .so loading may be blocked by SELinux context (E073).
The test script (test_sha1.sh) handles this internally:
  - Verifies .so and .pm file presence (always)
  - Attempts to load module and call SHA1 API
  - If "Permission denied" (HMDFS SELinux): exits 0 after verifying package contents
  - Any other load failure: exits 1 (real test failure, not silently swallowed)
"""
import os

from conan import ConanFile


class PerlDigestSHA1TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["perl-digest-sha1"].package_folder
        perl_lib = os.path.join(pkg_folder, "lib", "perl5")
        test_script = os.path.join(os.path.dirname(__file__), "test_sha1.sh")

        # R34: Run test script that calls actual SHA1 API (new, add, hexdigest)
        # The script verifies .so/.pm presence, loads the module, and calls SHA1 functions.
        # On OHOS HMDFS, "Permission denied" (E073) is tolerated — all other errors fail.
        self.run(f'sh "{test_script}" "{perl_lib}"', env="conanrun")
        self.output.info("Digest::SHA1 test passed (module verified or platform limitation acknowledged)")
