#!/usr/bin/env python3
"""Conan recipe for aws-checksums 0.2.10.

AWS checksums library providing CRC32C, CRC32, CRC64 NVME, SHA256, MD5
checksum computation. Built as static library for HarmonyOS PC (aarch64).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class AwschecksumsConan(ConanFile):
    name = "aws-checksums"
    version = "0.2.10"
    description = "AWS checksums library (CRC32C, CRC32, CRC64 NVME, SHA256, MD5)"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-checksums"
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
        # Generate CMakeDeps for find_package(aws-c-common)
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"

        # aws-c-common ships CMake modules (AwsCFlags, AwsCheckHeaders, etc.)
        # in lib/cmake/aws-c-common/modules/. Add to CMAKE_MODULE_PATH.
        aws_c_common = self.dependencies["aws-c-common"]
        module_path = "{}/lib/cmake/aws-c-common/modules".format(
            aws_c_common.package_folder
        )
        tc.cache_variables["CMAKE_MODULE_PATH"] = module_path

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
        self.cpp_info.libs = ["aws-checksums"]
        self.cpp_info.requires = ["aws-c-common::aws-c-common"]
