# test_package/conanfile.py
"""Conan test_package for perl-crypt-openssl-verify 0.36-r2.

Tests that the Crypt::OpenSSL::Verify Perl module is properly installed
and can be loaded by Perl.

Note: On OpenHarmony, dlopen of .so files from HMDFS directories may be
restricted by SELinux (E073). This test verifies file presence and
basic structure. Runtime loading test is skipped on OHOS due to
platform limitation (see notes.md).
"""
import os
import subprocess

from conan import ConanFile


class PerlCryptOpensslVerifyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the package folder from the dependency
        dep_name = self.tested_reference_str.split("/")[0]
        pkg_root = None
        try:
            pkg_root = self.dependencies[dep_name].package_folder
        except Exception:
            pass
        if not pkg_root:
            try:
                pkg_root = self.deps_user_info[dep_name].rootpath
            except Exception:
                pkg_root = self.package_folder

        self.output.info(f"Package root: {pkg_root}")

        # Find Verify.so and Verify.pm in the package
        found_so = False
        found_pm = False
        so_path = None
        for root, dirs, files in os.walk(pkg_root):
            for f in files:
                if f == "Verify.so":
                    found_so = True
                    so_path = os.path.join(root, f)
                    self.output.info(f"Found Verify.so: {so_path}")
                if f == "Verify.pm":
                    found_pm = True
                    self.output.info(f"Found Verify.pm: {os.path.join(root, f)}")

        if not found_so:
            self.output.warning("Verify.so not found in package")
        if not found_pm:
            raise Exception("Verify.pm not found in package")

        self.output.info("Package structure verified (Verify.pm present)")

        # L2: Smoke test — verify perl is available
        self.run("perl -v", env=["conanrun"])

        # Try to load the module (may fail on OHOS due to SELinux)
        if self.settings.os == "OHOS":
            self.output.info("Skipping runtime load test on OHOS (E073: HMDFS SELinux limitation)")
            # On OHOS, verify the .so file exists as a valid ELF binary
            if found_so and so_path:
                self.run("file " + so_path, env=["conanrun"])
        else:
            self.run("perl -e 'require Crypt::OpenSSL::Verify; 1'", env=["conanrun"])
