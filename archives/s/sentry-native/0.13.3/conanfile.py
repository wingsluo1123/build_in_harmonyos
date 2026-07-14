#!/usr/bin/env python3
"""Conan recipe for sentry-native 0.13.3 — CMake build system.

Sentry SDK for C, C++ and native applications.
Build: shared library, inproc backend, none transport (no curl on OHOS).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SentryNativeConan(ConanFile):
    name = "sentry-native"
    version = "0.13.3"
    description = "Sentry SDK for C, C++ and native applications"
    license = "MIT"
    homepage = "https://sentry.io/"

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

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
        # OHOS: no curl dev library available, disable HTTP transport
        tc.variables["SENTRY_TRANSPORT"] = "none"
        # Use in-process crash capture backend (no crashpad/breakpad deps)
        tc.variables["SENTRY_BACKEND"] = "inproc"
        # Disable upstream tests/examples — modulefinder link errors on OHOS,
        # test_package provides consumer-level verification instead
        tc.variables["SENTRY_BUILD_TESTS"] = "OFF"
        tc.variables["SENTRY_BUILD_EXAMPLES"] = "OFF"
        # OHOS: CMake lacks Platform/HarmonyOS module, so CMAKE_SYSTEM_PROCESSOR
        # is "unknown" — vendored libunwind needs "aarch64" for arch detection
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
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
        self.cpp_info.set_property("cmake_file_name", "sentry")
        self.cpp_info.set_property("cmake_target_name", "sentry::sentry")
        self.cpp_info.libs = ["sentry"]
