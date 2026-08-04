#!/usr/bin/env python3
"""Conan recipe for aws-c-event-stream 0.7.0 — AWS event-stream protocol codec.

Provides binary message framing and CRC validation for S3 Select, Kinesis,
DynamoDB Streams and other AWS services.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AwsceventstreamConan(ConanFile):
    name = "aws-c-event-stream"
    version = "0.7.0"
    description = "AWS event-stream 协议编解码库，用于 S3 Select、Kinesis 等服务的二进制消息分帧"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-event-stream"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aws-c-common/0.12.6")
        self.requires("aws-c-io/0.26.3")
        self.requires("aws-checksums/0.2.10")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        # BYO_CRYPTO=ON so aws-c-io's cmake config skips find_dependency(s2n)
        tc.variables["BYO_CRYPTO"] = "ON"
        # Point CMake to all dependency package folders so find_package and
        # aws_use_package find the AWS:: namespace targets, and transitive
        # find_dependency calls in installed cmake configs resolve correctly
        common = self.dependencies["aws-c-common"]
        cal = self.dependencies["aws-c-cal"]
        io = self.dependencies["aws-c-io"]
        checksums = self.dependencies["aws-checksums"]
        tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join([
            common.package_folder,
            cal.package_folder,
            io.package_folder,
            checksums.package_folder,
        ])
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
        self.cpp_info.libs = ["aws-c-event-stream"]
        self.cpp_info.requires = [
            "aws-c-common::aws-c-common",
            "aws-c-io::aws-c-io",
            "aws-checksums::aws-checksums",
        ]
