#!/usr/bin/env python3
"""Conan test_package for pkgconf 2.5.1.

Verifies the libpkgconf API is usable by creating a client, checking version,
and testing path_split functionality (R34: substantive test).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PkgconfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Fix compiler path in CMake toolchain file
        # CI profile points to /data/service/hnp/bin/clang which may not exist
        # on dev machines — only replace if the profile path is invalid
        profile_clang = '/data/service/hnp/bin/clang'
        profile_clangxx = '/data/service/hnp/bin/clang++'

        if not os.path.exists(profile_clang):
            clang = shutil.which('clang')
            clangxx = shutil.which('clang++')
            if clang:
                os.environ["CC"] = clang
            if clangxx:
                os.environ["CXX"] = clangxx

            # Also fix the CMake toolchain file if it has the wrong path
            gen_folder = self.generators_folder
            toolchain_file = os.path.join(gen_folder, "conan_toolchain.cmake")
            if os.path.exists(toolchain_file):
                with open(toolchain_file, 'r') as f:
                    content = f.read()
                if clang:
                    content = content.replace(profile_clang, clang)
                if clangxx:
                    content = content.replace(profile_clangxx, clangxx)
                with open(toolchain_file, 'w') as f:
                    f.write(content)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary directly (R34: substantive test)
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_pkgconf"), env="conanrun")
