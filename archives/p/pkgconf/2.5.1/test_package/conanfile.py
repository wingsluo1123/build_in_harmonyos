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
        # Fix compiler path in CMake toolchain file if CI profile path doesn't exist
        ci_clang = "/data/service/hnp/bin/clang"
        if not os.path.exists(ci_clang):
            local_clang = shutil.which("clang") or "/storage/Users/currentUser/usr/local/bin/clang"
            local_clangpp = shutil.which("clang++") or local_clang + "++"
            toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
            if os.path.exists(toolchain_file):
                with open(toolchain_file, 'r') as f:
                    content = f.read()
                content = content.replace(ci_clang, local_clang)
                content = content.replace(ci_clang + "++", local_clangpp)
                with open(toolchain_file, 'w') as f:
                    f.write(content)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary directly (R34: substantive test)
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_pkgconf"), env="conanrun")
