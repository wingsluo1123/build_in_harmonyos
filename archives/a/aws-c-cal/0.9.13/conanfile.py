#!/usr/bin/env python3
"""Conan recipe for aws-c-cal 0.9.13 — AWS Crypto Abstraction Layer.

Provides HMAC, block cipher, hash, RSA, ECDH and other cryptographic function
interfaces built on top of aws-c-common.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AwsccalConan(ConanFile):
    name = "aws-c-cal"
    version = "0.9.13"
    description = "AWS Crypto Abstraction Layer: HMAC, block cipher, hash, RSA, ECDH"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-cal"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # No generators declared here — CMakeToolchain is instantiated manually in
    # generate() so we can inject custom variables.
    # We deliberately do NOT use CMakeDeps: aws-c-cal's CMakeLists.txt calls
    # aws_use_package("aws-c-common") which sets the link target to
    # AWS::aws-c-common (the namespace from aws-c-common's own installed CMake
    # config).  CMakeDeps would instead create aws-c-common::aws-c-common and
    # the build would fail with "target AWS::aws-c-common not found".
    # Instead we point CMAKE_PREFIX_PATH at the aws-c-common package folder so
    # CMake finds its own config file and creates the correct AWS:: target.

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
        # No OpenSSL/AWS-LC available on HarmonyOS; build without crypto backend
        tc.variables["BYO_CRYPTO"] = "ON"
        # Point CMAKE_PREFIX_PATH to aws-c-common package so its own CMake
        # config (creating AWS::aws-c-common target) is found.
        aws_common = self.dependencies["aws-c-common"]
        tc.cache_variables["CMAKE_PREFIX_PATH"] = aws_common.package_folder
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
        self.cpp_info.libs = ["aws-c-cal"]
        self.cpp_info.set_property("cmake_file_name", "aws-c-cal")
        self.cpp_info.set_property("cmake_target_name", "aws-c-cal::aws-c-cal")
