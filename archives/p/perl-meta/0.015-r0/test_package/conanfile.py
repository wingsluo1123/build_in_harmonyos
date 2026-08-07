#!/usr/bin/env python3
"""Conan test_package — meta Perl XS module (perl-meta).

L1 test: Verify the Perl module .so exists in the package and call actual
meta API functions (meta::get_package + meta::package->get) to validate
functionality.

On OHOS with HMDFS, .so loading may be blocked by SELinux context (E073).
The test script (test_meta.sh) handles this internally:
  - Verifies .so and .pm file presence (always)
  - Attempts to load module and call meta::get_package + meta::package->get
  - If "Permission denied" (HMDFS SELinux): exits 0 after verifying package contents
  - Any other load failure: exits 1 (real test failure, not silently swallowed)
"""
import os

from conan import ConanFile


class PerlMetaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["perl-meta"].package_folder
        perl_lib = os.path.join(pkg_folder, "lib", "perl5")
        test_script = os.path.join(os.path.dirname(__file__), "test_meta.sh")

        # R34: Run test script that calls actual meta API (meta::get_package, meta::package->get)
        # The script verifies .so/.pm presence, loads the module, and calls meta functions.
        # On OHOS HMDFS, "Permission denied" (E073) is tolerated — all other errors fail.
        self.run(f'sh "{test_script}" "{perl_lib}"', env="conanrun")
        self.output.info("meta test passed (module verified or platform limitation acknowledged)")
