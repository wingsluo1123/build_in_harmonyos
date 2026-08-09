#!/usr/bin/env python3
"""Conan recipe for aws-c-cal 0.9.13.

aws-c-cal provides cryptographic abstraction layer for AWS SDK for C.
Build system: CMake (C99 library, depends on OpenSSL).
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AwsccalConan(ConanFile):
    name = "aws-c-cal"
    version = "0.9.13"
    description = "Cryptographic abstraction layer for AWS SDK for C"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-cal"
    url = "https://github.com/awslabs/aws-c-cal"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aws-c-common/0.14.3")
        self.requires("openssl/3.5.6.1")

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
        prefix_paths = [d.package_folder for d in self.dependencies.values() if hasattr(d, 'package_folder') and d.package_folder]
        vars_dict = {"CMAKE_PREFIX_PATH": ";".join(prefix_paths)} if prefix_paths else {}
        cmake.configure(variables=vars_dict)
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["aws-c-cal"]
        self.cpp_info.system_libs = ["pthread"]
