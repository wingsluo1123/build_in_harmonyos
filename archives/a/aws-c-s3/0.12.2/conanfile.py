#!/usr/bin/env python3
"""Conan recipe for aws-c-s3 0.12.2 — AWS S3 Client Library.

Provides high-level S3 API operations including object operations,
multipart uploads, and S3 Select. Depends on the full AWS CRT C library
stack: aws-c-common, aws-c-auth, aws-checksums, and transitively
aws-c-io, aws-c-http, aws-c-cal, aws-c-sdkutils, aws-c-compression,
aws-c-event-stream.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class Awscs3Conan(ConanFile):
    name = "aws-c-s3"
    version = "0.12.2"
    description = "AWS S3 Client Library — object operations, multipart uploads, S3 Select"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-s3"
    url = "https://github.com/awslabs/aws-c-s3"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aws-c-common/0.14.3")
        self.requires("aws-c-auth/0.10.1")
        self.requires("aws-checksums/0.2.10")
        # Transitive deps needed for headers (cpp_info.includedirs workaround)
        self.requires("aws-c-io/0.26.3")
        self.requires("aws-c-http/0.10.14")
        self.requires("aws-c-cal/0.9.13")
        self.requires("aws-c-sdkutils/0.2.4")
        self.requires("aws-c-compression/0.3.2")
        self.requires("aws-c-event-stream/0.7.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["ENABLE_S3_ENDPOINT_RESOLVER"] = "OFF"
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("aws-c-common", "cmake_target_name", "AWS::aws-c-common")
        deps.set_property("aws-c-auth", "cmake_target_name", "AWS::aws-c-auth")
        deps.set_property("aws-checksums", "cmake_target_name", "AWS::aws-checksums")
        deps.set_property("aws-c-io", "cmake_target_name", "AWS::aws-c-io")
        deps.set_property("aws-c-http", "cmake_target_name", "AWS::aws-c-http")
        deps.set_property("aws-c-cal", "cmake_target_name", "AWS::aws-c-cal")
        deps.set_property("aws-c-sdkutils", "cmake_target_name", "AWS::aws-c-sdkutils")
        deps.set_property("aws-c-compression", "cmake_target_name", "AWS::aws-c-compression")
        deps.set_property("aws-c-event-stream", "cmake_target_name", "AWS::aws-c-event-stream")
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
        self.cpp_info.libs = ["aws-c-s3"]
        self.cpp_info.includedirs = ["include"]
