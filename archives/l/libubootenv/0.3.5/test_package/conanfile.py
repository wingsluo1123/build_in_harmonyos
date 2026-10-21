#!/usr/bin/env python3
"""Conan test_package for libubootenv 0.3.5."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class LibubootenvTestConan(ConanFile):
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
        if can_run(self):
            test_bin = os.path.join(self.cpp.build.bindirs[0], "test_ubootenv")
            # OHOS: set LD_LIBRARY_PATH to find the shared library
            lib_dir = self.dependencies["libubootenv"].cpp_info.libdirs[0]
            self.run(f'LD_LIBRARY_PATH="{lib_dir}" {test_bin}')

            # OHOS-specific runtime test: dlopen the shared library
            dlopen_bin = os.path.join(self.cpp.build.bindirs[0], "test_dlopen")
            lib_path = os.path.join(lib_dir, "libubootenv.so")
            self.run(f'LD_LIBRARY_PATH="{lib_dir}" {dlopen_bin} {lib_path}')
