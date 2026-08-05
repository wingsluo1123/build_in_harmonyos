#!/usr/bin/env python3
"""Conan recipe for cpptoml v0.1.1 — CMake build system.

cpptoml is a header-only C++ TOML parser library.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CpptomlConan(ConanFile):
    name = "cpptoml"
    version = "v0.1.1"
    description = "C++ TOML configuration file parser (header-only)"
    license = "MIT"
    homepage = "https://github.com/skystrife/cpptoml"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        # Set BUILD_SHARED_LIBS based on shared option
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # cpptoml-specific: disable libc++ dependency (not available on OHOS)
        tc.variables["ENABLE_LIBCXX"] = "OFF"
        # Don't build examples in the package
        tc.variables["CPPTOML_BUILD_EXAMPLES"] = "OFF"
        # CMake 4.x compatibility (project requires CMake 3.1.0)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
