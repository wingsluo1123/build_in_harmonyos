#!/usr/bin/env python3
"""Conan test_package — perl-set-object 1.43-r0

L1 test: verify Set::Object module package structure and functionality.
Runs the shell test script which loads the module and exercises set operations.
On HarmonyOS, SELinux HMDFS may block .so loading from user space (E046);
the test script handles expected failures gracefully.
"""
import os

from conan import ConanFile


class PerlSetObjectTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Locate the package folder via the dependency
        pkg = None
        for name, dep in self.dependencies.items():
            pkg = dep.package_folder
            if pkg:
                break

        if not pkg:
            raise AssertionError("Could not find perl-set-object dependency")

        self.output.info(f"Package folder: {pkg}")

        # --- Step 1: Structural verification ---
        lib_dir = os.path.join(pkg, "lib")
        if not os.path.exists(lib_dir):
            raise AssertionError(f"lib/ directory not found in package: {pkg}")

        so_found = False
        pm_found = False
        weak_pm_found = False
        so_path = None
        for root, dirs, files in os.walk(pkg):
            for f in files:
                fpath = os.path.join(root, f)
                if f == "Object.so":
                    so_found = True
                    self.output.info(f"Found Object.so: {fpath}")
                    so_path = fpath
                if f == "Object.pm":
                    pm_found = True
                    self.output.info(f"Found Object.pm: {fpath}")
                if f == "Weak.pm":
                    weak_pm_found = True
                    self.output.info(f"Found Weak.pm: {fpath}")

        if not so_found:
            raise AssertionError("Object.so not found in package")
        if not pm_found:
            raise AssertionError("Object.pm not found in package")
        if not weak_pm_found:
            raise AssertionError("Set/Object/Weak.pm not found in package")

        self.output.info("Set::Object package structure verified OK")

        # --- Step 2: Static ELF analysis via self.run() ---
        if so_path and os.path.exists(so_path):
            self.output.info("Running static ELF analysis on Object.so...")
            self.run(f'readelf -d "{so_path}"', env="conanrun")
            self.run(f'nm -D "{so_path}" | grep boot_Set__Object', env="conanrun")

        # --- Step 3: Functional test via self.run() ---
        # Runs the shell test script which loads Set::Object and exercises
        # insert/remove/union/intersection operations.
        # PERL5LIB is set by runenv_info from package_info().
        test_script = os.path.join(self.source_folder, "test_set_object.sh")
        self.run(f'sh "{test_script}"', env="conanrun")

        self.output.info("=== Test package verification complete ===")
