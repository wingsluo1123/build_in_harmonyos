#!/usr/bin/env python3
"""Conan recipe for aws-checksums 0.2.10 — AWS efficient checksum computation library.

Supports CRC32/CRC32C (NEON SIMD accelerated), CRC64, MD5 and SHA.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class AwsChecksumsConan(ConanFile):
    name = "aws-checksums"
    version = "0.2.10"
    description = "AWS 高效校验和计算库，支持 CRC32/CRC32C/CRC64/MD5/SHA"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-checksums"
    url = "https://github.com/awslabs/aws-checksums"

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
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"

        # Create a helper cmake file that APPENDS to CMAKE_MODULE_PATH
        # (tc.variables uses set(... CACHE ...) which gets shadowed by the
        # regular variable that the toolchain already creates via list(PREPEND))
        aws_cc = self.dependencies["aws-c-common"]
        modules_dir = os.path.join(aws_cc.package_folder, "lib", "cmake", "aws-c-common", "modules")
        helper_file = os.path.join(self.generators_folder, "aws_modules_path.cmake")
        with open(helper_file, "w") as f:
            f.write(f'list(APPEND CMAKE_MODULE_PATH "{modules_dir}")\n')
        tc.variables["CMAKE_PROJECT_INCLUDE"] = helper_file

        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

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
