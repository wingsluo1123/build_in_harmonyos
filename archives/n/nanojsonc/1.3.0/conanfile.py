#!/usr/bin/env python3
"""Conan recipe — nanojsonc 1.3.0 (CMake project).

nanoJSONc is a C-based event-driven JSON parser (~250 LOC, no malloc, no deps).
Source: https://github.com/open-source-patterns/nanojsonc (tag 1.3.0)
Patch 0001: fix install header path double-nesting (include/nanojsonc/nanojsonc/parser.h)
            so consumers can `#include <nanojsonc/parser.h>` via INSTALL_INTERFACE.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class NanojsoncConan(ConanFile):
    name = "nanojsonc"
    version = "1.3.0"
    description = "nanoJSONc - Event-Driven JSON Parser for C (no malloc, no deps)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/open-source-patterns/nanojsonc"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Non system-name library: static by default, keep shared opt-in.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream tests are exercised locally in finish; recipe packages library only.
        tc.variables["BUILD_TESTS"] = "OFF"
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
        self.cpp_info.libs = ["nanojsonc"]
        self.cpp_info.set_property("cmake_file_name", "nanojsonc")
        self.cpp_info.set_property("cmake_target_name", "nanojsonc::nanojsonc")