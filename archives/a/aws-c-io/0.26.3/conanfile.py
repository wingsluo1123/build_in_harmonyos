#!/usr/bin/env python3
"""Conan recipe for aws-c-io 0.26.3 — AWS C SDK IO and TLS abstraction layer.

Provides event loop, socket channel, and async IO abstraction.
Built with BYO_CRYPTO=ON to skip s2n TLS dependency on HarmonyOS.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AwscioConan(ConanFile):
    name = "aws-c-io"
    version = "0.26.3"
    description = "AWS C SDK 的 IO 和 TLS 抽象层，提供事件循环、Socket 通道和异步 IO"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-io"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aws-c-common/0.12.6")
        self.requires("aws-c-cal/0.9.13")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        # BYO_CRYPTO=ON disables s2n TLS dependency (not available on HarmonyOS)
        tc.variables["BYO_CRYPTO"] = "ON"
        # HarmonyOS is POSIX-compatible with Linux; override for platform detection
        # so CMake includes source/linux/*.c and source/posix/*.c
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Point CMake to aws-c-common and aws-c-cal installed cmake configs
        # This makes find_package(aws-c-common) and aws_use_package(aws-c-cal)
        # use the installed configs which create AWS:: namespace targets
        common = self.dependencies["aws-c-common"]
        cal = self.dependencies["aws-c-cal"]
        tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join([
            common.package_folder,
            cal.package_folder,
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
        self.cpp_info.libs = ["aws-c-io"]
        self.cpp_info.requires = ["aws-c-common::aws-c-common", "aws-c-cal::aws-c-cal"]
