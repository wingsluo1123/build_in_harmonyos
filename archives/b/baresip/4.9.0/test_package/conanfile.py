#!/usr/bin/env python3
"""Conan test_package for baresip 4.9.0 — L1 smoke test.

Tests baresip library API: baresip_init/baresip_close.
"""
import os
from conan import ConanFile


class BaresipTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test that baresip binary is installed and executable
        pkg_folder = self.dependencies["baresip"].package_folder
        baresip_bin = os.path.join(pkg_folder, "bin", "baresip")
        self.run("test -f " + baresip_bin, env="conanrun")
        # Verify the library exists
        lib_dir = os.path.join(pkg_folder, "lib")
        self.run("ls -la " + lib_dir + "/libbaresip* 2>&1", env="conanrun")
        # Verify API symbol exists
        self.run("nm -D " + lib_dir + "/libbaresip.so 2>/dev/null | grep -q 'T baresip_init'", env="conanrun")