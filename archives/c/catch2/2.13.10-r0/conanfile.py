#!/usr/bin/env python3
"""Conan recipe for catch2 2.13.10-r0 (header-only CMake)."""

from conan import ConanFile
from conan.tools.files import get
from conan.tools.cmake import CMakeToolchain


class Catch2Recipe(ConanFile):
    name = "catch2"
    version = "2.13.10-r0"
    package_type = "header-library"

    description = "A modern, C++-native, header-only, test framework for unit-tests"
    license = "BSL-1.0"
    homepage = "https://github.com/catchorg/Catch2"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("testing", "unit-testing", "header-only")

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version])

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = False
        tc.variables["CATCH_BUILD_TESTING"] = False
        tc.variables["CATCH_BUILD_EXAMPLES"] = False
        tc.variables["CATCH_INSTALL_DOCS"] = False
        tc.generate()

    def build(self):
        self.run(
            f'cmake -S "{self.source_folder}" -B "{self.build_folder}" '
            f'-DCMAKE_TOOLCHAIN_FILE="generators/conan_toolchain.cmake" '
            f'-DBUILD_TESTING=OFF -DCATCH_BUILD_TESTING=OFF '
            f'-DCATCH_BUILD_EXAMPLES=OFF -DCATCH_INSTALL_DOCS=OFF'
        )

    def package(self):
        self.run(f'cmake --install "{self.build_folder}" --prefix "{self.package_folder}"')

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []