# test_package/conanfile.py
"""Conan test_package for perl-crypt-openssl-x509 2.0.1-r1.

Tests that the Crypt::OpenSSL::X509 Perl module files are properly packaged.

Note: On OpenHarmony, dlopen of .so files from HMDFS directories may be
restricted by SELinux (E073). This test verifies file presence and
basic structure. Runtime loading test is skipped on OHOS due to
platform limitation (see notes.md).
"""
import os

from conan import ConanFile


class PerlCryptOpensslX509TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the dependency's package folder
        pkg = None
        for _, dep in self.dependencies.items():
            if dep.package_folder:
                pkg = dep.package_folder
                break

        if not pkg:
            pkg = self.package_folder

        self.output.info(f"Package root: {pkg}")

        # Run test script to verify package structure
        # On OHOS, runtime dlopen is restricted by SELinux (E073),
        # so the test script checks file presence only.
        test_script = os.path.join(self.recipe_folder, "test_x509.sh")
        self.run(f'sh "{test_script}" "{pkg}"')
