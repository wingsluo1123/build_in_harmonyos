#!/usr/bin/env python3
"""Conan test_package — PerlIO::utf8_strict Perl XS module.

L1 test: Verify the Perl module .so exists in the package and call actual
PerlIO::utf8_strict API (write+read UTF-8 via :utf8_strict layer) to validate functionality.

On OHOS with HMDFS, .so loading may be blocked by SELinux context (E073).
The test script (test_utf8_strict.sh) handles this internally:
  - Verifies .so and .pm file presence (always)
  - Attempts to load module and write/read UTF-8 files via :utf8_strict layer
  - If "Permission denied" (HMDFS SELinux): exits 0 after verifying package contents
  - Any other load failure: exits 1 (real test failure, not silently swallowed)
"""
import os

from conan import ConanFile


class PerlPerlIOUtf8StrictTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["perl-perlio-utf8_strict"].package_folder
        perl_lib = os.path.join(pkg_folder, "lib", "perl5")
        test_script = os.path.join(os.path.dirname(__file__), "test_utf8_strict.sh")

        # R34: Run test script that calls actual PerlIO::utf8_strict API
        # The script verifies .so/.pm presence, loads the module, and tests UTF-8 IO.
        # On OHOS HMDFS, "Permission denied" (E073) is tolerated — all other errors fail.
        self.run(f'sh "{test_script}" "{perl_lib}"', env="conanrun")
        self.output.info("PerlIO::utf8_strict test passed (module verified or platform limitation acknowledged)")
