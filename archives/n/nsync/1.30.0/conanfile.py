#!/usr/bin/env python3
"""Conan recipe for nsync 1.30.0 — Google synchronization primitives library."""

import os
from conan import ConanFile
from conan.tools.files import get, copy, rename, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class NsyncConan(ConanFile):
    name = "nsync"
    version = "1.30.0"
    description = "A C library that exports various synchronization primitives, such as mutexes"
    license = "Apache-2.0"
    homepage = "https://github.com/google/nsync"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Rename BUILD -> BUILD.bazel to avoid conflict with build/ directory
        # on OHOS case-insensitive filesystem (HMDFS).
        build_file = os.path.join(self.source_folder, "BUILD")
        if os.path.isfile(build_file):
            os.rename(build_file, os.path.join(self.source_folder, "BUILD.bazel"))

    def generate(self):
        tc = CMakeToolchain(self)
        # nsync is a static library, not a system library
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # OHOS CMake platform detection: nsync's CMakeLists.txt checks for
        # CMAKE_SYSTEM_NAME == "Linux" to pick the correct platform
        # sources (futex semaphore, linux includes). Since OHOS is
        # Linux-compatible at this level, tell CMake to treat it as Linux.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
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
        self.cpp_info.libs = ["nsync", "nsync_cpp"]
