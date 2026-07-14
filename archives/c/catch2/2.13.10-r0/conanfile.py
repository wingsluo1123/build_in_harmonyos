#!/usr/bin/env python3
"""Conan recipe for catch2 2.13.10-r0 (header-only CMake)."""

from conan import ConanFile
from conan.tools.files import get


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
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        self.run(
            "cmake -S . -B builddir "
            "-DBUILD_TESTING=OFF -DCATCH_BUILD_TESTING=OFF "
            "-DCATCH_BUILD_EXAMPLES=OFF -DCATCH_INSTALL_DOCS=OFF",
            cwd=self.source_folder
        )

    def package(self):
        self.run(
            "cmake --install builddir --prefix=" + self.package_folder,
            cwd=self.source_folder
        )

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []