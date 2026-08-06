#!/usr/bin/env python3
"""Conan test_package for grilo-plugins 0.3.16.

Tests that the plugin shared libraries are installed and loadable.
Uses dlopen to verify the plugin .so files can be dynamically loaded,
satisfying R34 (test must substantively depend on the tested package).
"""
import os
import glob

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GriloPluginsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Verify plugin libraries exist in the package
        pkg_libdir = os.path.join(self.deps_info["grilo-plugins"].package_folder, "lib")
        plugins_dir = os.path.join(pkg_libdir, "grilo-0.3")
        so_files = glob.glob(os.path.join(plugins_dir, "libgrl*.so"))
        if not so_files:
            # Fallback: check lib dir directly
            so_files = glob.glob(os.path.join(pkg_libdir, "libgrl*.so"))
        assert so_files, f"No grilo-plugins .so files found in {pkg_libdir}"
        self.output.info(f"Found {len(so_files)} plugin libraries")

        # Run the test binary which loads a plugin via dlopen
        self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_grilo_plugins')}", env="conanrun")
