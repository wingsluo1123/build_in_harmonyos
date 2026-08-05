#!/usr/bin/env python3
"""Conan recipe for Bear 3.1.6 — OHOS PC platform adaptation.

Bear is a tool that generates compilation database for clang tooling.
It uses CMake superbuild pattern with ExternalProject for dependencies
(grpc, protobuf, fmt, spdlog, nlohmann_json).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BearConan(ConanFile):
    name = "bear"
    version = "3.1.6"
    description = "BuildEAR — tool to generate compilation database for clang tooling"
    license = "GPL-3.0"
    homepage = "https://github.com/rizsotto/Bear"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Export fetch_submodules.sh as a recipe source file
        copy(self, "fetch_submodules.sh", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        pass  # All deps built via ExternalProject (bundled)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Copy fetch_submodules.sh to the correct location in source tree
        copy(self, "fetch_submodules.sh", self.export_sources_folder,
             os.path.join(self.source_folder, "third_party", "grpc"))

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_UNIT_TESTS"] = False
        tc.variables["ENABLE_FUNC_TESTS"] = False
        tc.generate()

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
        bin_path = os.path.join(self.package_folder, "bin")
        self.output.info(f"Bear binaries installed to: {bin_path}")
