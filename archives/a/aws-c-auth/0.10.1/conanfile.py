#!/usr/bin/env python3
"""Conan recipe for aws-c-auth 0.10.1 — AWS SDK for C authentication library.

Provides AWS credential management, SigV4 signing, IAM role authentication.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AwscauthConan(ConanFile):
    name = "aws-c-auth"
    version = "0.10.1"
    description = "AWS SDK for C authentication library: credentials, SigV4 signing, IAM roles"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-auth"
    url = "https://github.com/awslabs/aws-c-auth"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aws-c-common/0.12.6")
        self.requires("aws-c-cal/0.9.13")
        self.requires("aws-c-sdkutils/0.2.4")
        self.requires("aws-c-io/0.26.3")
        self.requires("aws-c-http/0.10.14")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
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
        self.cpp_info.libs = ["aws-c-auth"]
        self.cpp_info.requires = ["aws-c-common::aws-c-common", "aws-c-cal::aws-c-cal",
                                  "aws-c-sdkutils::aws-c-sdkutils", "aws-c-io::aws-c-io",
                                  "aws-c-http::aws-c-http"]
