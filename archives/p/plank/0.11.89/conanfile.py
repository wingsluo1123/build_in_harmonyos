#!/usr/bin/env python3
"""Conan recipe for plank 0.11.89 — memory instrumentation library.

plank provides two static libraries:
  - libplank.a   : C memory pool allocator (palloc/pfree) with mmap + mprotect
  - libplankmm.a : C++ wrapper that overrides global new/delete

Build system: CMake (cmake_minimum_required 2.6, policy override 3.5).
No external dependencies. Only uses POSIX libc (mmap, mprotect, munmap, atexit).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PlankConan(ConanFile):
    name = "plank"
    version = "0.11.89"
    description = "Memory instrumentation library — C pool allocator (palloc/pfree) and C++ new/delete override"
    license = "GPL-3.0"
    homepage = "https://github.com/osen/plank"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x removed compatibility with cmake_minimum_required < 3.5
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # E092: CMake doesn't have HarmonyOS platform module, use Linux
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Manual package copy — upstream CMakeLists.txt has no install target
        src_include = os.path.join(self.source_folder, "src")
        copy(self, "*.h", src=src_include, dst=os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "libplank.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libplankmm.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "plank")
        # C component
        self.cpp_info.components["plank"].libs = ["plank"]
        self.cpp_info.components["plank"].includedirs = ["include"]
        self.cpp_info.components["plank"].system_libs = ["c"]
        # C++ wrapper component
        self.cpp_info.components["plankmm"].libs = ["plankmm"]
        self.cpp_info.components["plankmm"].includedirs = ["include"]
        self.cpp_info.components["plankmm"].requires = ["plank"]
        self.cpp_info.components["plankmm"].system_libs = ["c"]
