#!/usr/bin/env python3
"""Conan recipe for curlcpp 3.1 — C++ wrapper for CURL (libcurl).

Build system: CMake
R26: Static linking (BUILD_SHARED_LIBS=OFF)
R27: Dependencies use @ohpcd/stable (curl/8.15.0@ohpcd/stable declared,
     but not yet published to conan remote — using system libcurl as fallback)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CurlcppConan(ConanFile):
    name = "curlcpp"
    version = "3.1"
    description = "Object oriented C++ wrapper for CURL (libcurl)"
    license = "MIT"
    homepage = "https://github.com/JosephP91/curlcpp/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: Dependencies must use @ohpcd/stable
        # curlcpp depends on libcurl (curl/8.15.0@ohpcd/stable)
        # NOTE: curl/8.15.0 is in archives (status: built) but not yet published
        # to the ohpcd conan remote. Using system libcurl as fallback via
        # CMAKE_PREFIX_PATH in generate(). Uncomment when curl is published:
        # self.requires("curl/8.15.0@ohpcd/stable")
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: Static linking for terminal tools
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        # Use find_package(CURL) instead of pkg-config
        tc.variables["CURLCPP_USE_PKGCONFIG"] = "OFF"
        # Fallback: point CMake to system libcurl installation
        # (remove when curl/8.15.0@ohpcd/stable is published)
        sys_prefix = os.path.expanduser("~/usr/local")
        if os.path.isdir(os.path.join(sys_prefix, "lib", "libcurl.a")):
            tc.variables["CMAKE_PREFIX_PATH"] = sys_prefix
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
        self.cpp_info.libs = ["curlcpp"]
