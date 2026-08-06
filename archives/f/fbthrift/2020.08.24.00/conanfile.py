#!/usr/bin/env python3
"""Conan recipe for fbthrift — Facebook Thrift compiler and runtime libraries.

Builds thrift1 compiler binary and thrift-core library.
Uses CMake build system with OHOS platform support.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class FbthriftConan(ConanFile):
    name = "fbthrift"
    version = "2020.08.24.00"
    description = "Facebook Thrift is a high-performance cross-language RPC framework with compiler and runtime libraries"
    license = "Apache-2.0"
    homepage = "https://github.com/facebook/fbthrift"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "compiler_only": [True, False],
    }
    default_options = {
        "shared": False,
        "compiler_only": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/1.1.1w")
        self.requires("gflags/2.2.2")
        self.requires("glog/0.7.1")
        self.requires("zlib/1.3.1")
        self.requires("zstd/1.5.6")
        # These dependencies need to be published to ohpcd registry first
        # self.requires("folly/v2024.11.18.00")
        # self.requires("fizz/v2024.11.18.00")
        # self.requires("fmt/11.2.0")
        # self.requires("wangle/v2024.11.18.00")

    def build_requirements(self):
        # flex and bison are build tools, not runtime dependencies
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS platform settings
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "17"
        # Build options
        tc.cache_variables["BUILD_TESTS"] = "OFF"
        if self.options.compiler_only:
            tc.cache_variables["compiler_only"] = "ON"
        else:
            tc.cache_variables["compiler_only"] = "OFF"
        # GLOG compatibility
        tc.variables["CMAKE_CXX_FLAGS"] = "-DGLOG_USE_GLOG_EXPORT -D__OHOS__"
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
        # Thrift compiler binary
        self.cpp_info.bindirs = ["bin"]
        # Libraries
        self.cpp_info.libs = [
            "thrift-core",
            "compiler_generators",
            "compiler_lib",
            "compiler_base",
            "compiler_ast",
            "mustache_lib",
        ]
        self.cpp_info.includedirs = ["include"]
