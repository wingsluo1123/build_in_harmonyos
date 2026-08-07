#!/usr/bin/env python3
"""Conan test_package — match::simple::XS Perl XS module.

L1 test: Verify the Perl module .so exists in the package and call actual
match() and is_regexp() API functions to validate functionality.

On OHOS with HMDFS, .so loading may be blocked by SELinux context (E073).
The test script (test_match_simple_xs.sh) handles this internally:
  - Verifies .so and .pm file presence (always)
  - Attempts to load module and call match() + is_regexp() API
  - If "Permission denied" (HMDFS SELinux): exits 0 after verifying package contents
  - Any other load failure: exits 1 (real test failure, not silently swallowed)
"""
import os

from conan import ConanFile


class PerlMatchSimpleXsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["perl-match-simple-xs"].package_folder
        perl_lib = os.path.join(pkg_folder, "lib", "perl5")
        test_script = os.path.join(os.path.dirname(__file__), "test_match_simple_xs.sh")

        # R34: Run test script that calls actual match::simple::XS API (match + is_regexp)
        # The script verifies .so/.pm presence, loads the module, and calls match() function.
        # On OHOS HMDFS, "Permission denied" (E073) is tolerated — all other errors fail.
        self.run(f'sh "{test_script}" "{perl_lib}"', env="conanrun")
        self.output.info("match::simple::XS test passed (module verified or platform limitation acknowledged)")
