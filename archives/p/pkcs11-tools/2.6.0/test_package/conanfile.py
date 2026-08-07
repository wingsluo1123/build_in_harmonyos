#!/usr/bin/env python3
"""Conan test_package for pkcs11-tools 2.6.0 — command-line tool test.

Verifies that the installed p11ls binary works and reports version info.
"""
import os

from conan import ConanFile


class Pkcs11ToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find p11ls in the package bin directory
        for dep in self.dependencies.values():
            if dep.ref.name == "pkcs11-tools":
                bin_dir = os.path.join(dep.package_folder, "bin")
                p11ls = os.path.join(bin_dir, "p11ls")
                if not os.path.exists(p11ls):
                    raise Exception(f"p11ls binary not found at {p11ls}")
                # Run p11ls -V and capture output to verify version string
                # p11ls -V may return non-zero on some platforms when no PKCS#11 token is present
                output = self.run(f'"{p11ls}" -V', env=["conanrun"], stdout=True)
                if "pkcs11-tools" not in str(output):
                    raise Exception("p11ls -V did not output expected version string")
                return
        raise Exception("pkcs11-tools dependency not found")
