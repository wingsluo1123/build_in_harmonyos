#!/usr/bin/env python3
"""Conan recipe for protobuf 21.12 (3.21.12).

Google's data serialization format library and compiler.
Build system: CMake.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ProtobufConan(ConanFile):
    name = "protobuf"
    version = "21.12"
    description = "Google's data serialization format library and compiler"
    license = "BSD-3-Clause"
    homepage = "https://github.com/protocolbuffers/protobuf"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: dependency references must use @ohpcd/stable
        self.requires("zlib/1.3.1@ohpcd/stable")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake doesn't recognize HarmonyOS as a platform, override to Linux
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # CMake build configuration (matching historical build parameters)
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.variables["protobuf_BUILD_TESTS"] = "OFF"
        tc.variables["protobuf_BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["protobuf_BUILD_PROTOC_BINARIES"] = "ON"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
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
        # Main protobuf library
        self.cpp_info.libs = ["protobuf", "protobuf-lite", "protoc"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
