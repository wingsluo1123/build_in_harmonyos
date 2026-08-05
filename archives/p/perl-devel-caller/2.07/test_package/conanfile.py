#!/usr/bin/env python3
"""Conan test_package — Devel-Caller 2.07 (Perl XS module)

Verifies Caller.so is a valid ELF with the boot_Devel__Caller XS entry
point symbol. Uses readelf instead of dlopen because Caller.so has
unresolved Perl interpreter symbols that require the Perl runtime
to resolve at load time.
"""
import os

from conan import ConanFile


class DevelCallerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate Caller.so in the package folder
        pkg_dir = self.dependencies[self.tested_reference_str].package_folder
        so_path = None

        for root, dirs, files in os.walk(pkg_dir):
            for f in files:
                if f == "Caller.so":
                    so_path = os.path.join(root, f)
                    break
            if so_path:
                break

        assert so_path, "Caller.so not found in package"

        self.output.info(f"Testing Caller.so at: {so_path}")

        # Run readelf-based verification script
        test_script = os.path.join(self.recipe_folder, "test.sh")
        self.run(f'sh "{test_script}" "{so_path}"', env="conanrun")
