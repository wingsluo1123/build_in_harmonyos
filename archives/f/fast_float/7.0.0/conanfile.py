#!/usr/bin/env python3
"""Conan recipe for fast_float 7.0.0 and its fast_float CLI."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class FastFloatConan(ConanFile):
    name = "fast_float"
    version = "7.0.0"
    description = "Fast C++ floating-point parser and command-line tool"
    license = "Apache-2.0 OR MIT OR BSL-1.0"
    homepage = "https://github.com/fastfloat/fast_float"
    # The package contains both a header-only library and a CLI executable.
    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "fast_float_cli.cpp",
            self.recipe_folder,
            os.path.join(self.export_sources_folder, "tools"),
        )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["FASTFLOAT_TEST"] = False
        toolchain.variables["FASTFLOAT_BENCHMARKS"] = False
        toolchain.variables["FASTFLOAT_INSTALL"] = True
        toolchain.variables["FASTFLOAT_TOOLS"] = True
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "FastFloat")
        self.cpp_info.set_property("cmake_target_name", "FastFloat::fast_float")
