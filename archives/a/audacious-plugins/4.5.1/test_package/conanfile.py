#!/usr/bin/env python3
"""Conan test_package for audacious-plugins.

Verifies that the package contains valid plugin .so files by using dlopen
to load a plugin and check its ELF shared object structure. This is a
substantive test per R34 (must depend on the tested package).
"""
import os
import glob

from conan import ConanFile


class AudaciousPluginsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        pass

    def build(self):
        # Compile the test program using dlopen to check plugin validity
        cc = str(self.settings.compiler) if self.settings.compiler else "clang"
        cflags = "-fPIC -O2"
        ldflags = "-ldl"
        self.run(f"{cc} {cflags} -o test_plugin_loader test.c {ldflags}")

    def test(self):
        # Find plugin .so files in the package
        pkg_root = self.deps_cpp_info["audacious-plugins"].rootpath
        plugin_files = glob.glob(os.path.join(pkg_root, "lib", "audacious", "*", "*.so"))
        if not plugin_files:
            raise Exception("No .so plugin files found in package!")
        # Run the test program to verify at least one plugin is loadable
        self.run(f"./test_plugin_loader {plugin_files[0]}")
