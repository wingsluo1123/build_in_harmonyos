#!/usr/bin/env python3
"""Conan recipe for aws-c-sdkutils 0.2.4 — AWS SDK Utils Library.

Provides utility functions for AWS SDKs including checksums,
encoding/decoding, and other common operations.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class AwscsdkutilsConan(ConanFile):
    name = "aws-c-sdkutils"
    version = "0.2.4"
    description = "AWS SDK Utils Library — utility functions for AWS SDKs"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-sdkutils"
    url = "https://github.com/awslabs/aws-c-sdkutils"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aws-c-common/0.14.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("aws-c-common", "cmake_target_name", "AWS::aws-c-common")
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        aws_common = self.dependencies["aws-c-common"]
        modules_dir = os.path.join(
            aws_common.package_folder,
            "lib", "cmake", "aws-c-common", "modules",
        )
        cmake.configure(variables={"CMAKE_MODULE_PATH": modules_dir})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["aws-c-sdkutils"]
        self.cpp_info.includedirs = ["include"]
