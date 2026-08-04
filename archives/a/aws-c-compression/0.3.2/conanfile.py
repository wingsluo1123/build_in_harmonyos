#!/usr/bin/env python3
"""Conan recipe for aws-c-compression 0.3.2 — AWS Huffman encoding/decoding for HTTP/2 HPACK."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AwsccompressionConan(ConanFile):
    name = "aws-c-compression"
    version = "0.3.2"
    description = "AWS C 库中的 Huffman 编码/解码组件，为 HTTP/2 HPACK 压缩提供基础"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-compression"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aws-c-common/0.12.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        # aws-c-common installs its own cmake config (AWS:: namespace + modules)
        # Point find_package to the installed config instead of CMakeDeps-generated one
        common = self.dependencies["aws-c-common"]
        common_cmake_dir = os.path.join(common.package_folder, "lib", "cmake", "aws-c-common")
        tc.cache_variables["aws-c-common_DIR"] = common_cmake_dir
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
        self.cpp_info.libs = ["aws-c-compression"]
        self.cpp_info.requires = ["aws-c-common::aws-c-common"]
