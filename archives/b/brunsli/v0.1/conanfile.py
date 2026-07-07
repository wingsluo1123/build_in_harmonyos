#!/usr/bin/env python3
"""Conan recipe for brunsli — JPEG Brunsli compression codec (Brotli-based).

Build system: CMake (brotli provided via Conan, googletest skipped)
Source: https://github.com/google/brunsli
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BrunsliConan(ConanFile):
    name = "brunsli"
    version = "v0.1"
    description = "JPEG Brunsli compression codec (Brotli-based JPEG recompression)"
    license = "Apache-2.0"
    homepage = "https://github.com/google/brunsli"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("brotli/1.0.7")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Remove Bazel BUILD file that conflicts with cmake build/ dir (case-insensitive FS)
        bazel_build = os.path.join(self.source_folder, "BUILD")
        if os.path.isfile(bazel_build):
            os.remove(bazel_build)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # E092: CMake does not recognize HarmonyOS
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Patch third_party/CMakeLists.txt to use Conan-provided brotli
        tp_cmake = os.path.join(self.source_folder, "third_party", "CMakeLists.txt")
        if os.path.isfile(tp_cmake):
            with open(tp_cmake, "w") as f:
                f.write("""# Patched by Conan: brotli provided via Conan, googletest skipped
find_package(brotli REQUIRED)
# Create alias targets that brunsli.cmake expects
if(NOT TARGET brotlicommon-static)
  add_library(brotlicommon-static INTERFACE)
  target_link_libraries(brotlicommon-static INTERFACE brotli::brotli)
endif()
if(NOT TARGET brotlidec-static)
  add_library(brotlidec-static INTERFACE)
  target_link_libraries(brotlidec-static INTERFACE brotli::brotli)
endif()
if(NOT TARGET brotlienc-static)
  add_library(brotlienc-static INTERFACE)
  target_link_libraries(brotlienc-static INTERFACE brotli::brotli)
endif()
""")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["brunslidec-c", "brunslienc-c"]
