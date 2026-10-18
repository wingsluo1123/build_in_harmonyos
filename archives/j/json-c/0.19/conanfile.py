#!/usr/bin/env python3
"""Conan recipe for json-c 0.19 — CMake-based JSON library in C.

json-c is a pure C library with no external dependencies.
Build system: CMake (cmake_minimum_required 3.9).
"""
from conan import ConanFile
import os

from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class JsoncConan(ConanFile):
    name = "json-c"
    version = "0.19"
    description = "JSON library in C"
    license = "MIT"
    homepage = "https://github.com/json-c/json-c"
    url = "https://github.com/json-c/json-c"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

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
        tc.variables["BUILD_TESTING"] = False
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if str(self.settings.os) == "OHOS":
            # The OHOS clang wrapper supplies a link-only signing flag during C compilation.
            # Preserve upstream -Werror for other diagnostics while allowing that one warning.
            tc.cache_variables["CMAKE_C_FLAGS"] = "-Wno-error=unused-command-line-argument"
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["json-c"]
        self.cpp_info.set_property("cmake_file_name", "json-c")
        self.cpp_info.set_property("pkg_config_name", "json-c")
