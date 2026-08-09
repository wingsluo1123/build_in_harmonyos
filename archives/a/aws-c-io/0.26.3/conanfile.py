#!/usr/bin/env python3
"""Conan recipe for aws-c-io 0.26.3 — AWS SDK for C IO and TLS abstraction layer.

Provides event loop, socket channel, and async IO abstractions.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class AwscioConan(ConanFile):
    name = "aws-c-io"
    version = "0.26.3"
    description = "AWS C SDK 的 IO 和 TLS 抽象层，提供事件循环、Socket 通道和异步 IO"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-io"
    url = "https://github.com/awslabs/aws-c-io"

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
        # BYO_CRYPTO disables s2n TLS dependency (s2n not available on HarmonyOS yet)
        tc.variables["BYO_CRYPTO"] = "ON"
        # Add aws-c-common cmake modules to CMAKE_MODULE_PATH (for AwsCFlags, AwsFindPackage, etc.)
        aws_common = self.dependencies["aws-c-common"]
        modules_dir = os.path.join(aws_common.package_folder, "lib", "cmake", "aws-c-common", "modules")
        tc.cache_variables["CMAKE_MODULE_PATH"] = modules_dir
        tc.generate()

        # Use CMakeDeps to generate proper cmake config files for dependencies
        deps = CMakeDeps(self)
        # aws-c-common installs aws-c-common-config.cmake with AWS::aws-c-common target
        deps.set_property("aws-c-common", "cmake_target_name", "AWS::aws-c-common")
        # aws-c-cal installs aws-c-cal-config.cmake with AWS::aws-c-cal target
        deps.set_property("aws-c-cal", "cmake_target_name", "AWS::aws-c-cal")
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
        self.cpp_info.libs = ["aws-c-io"]
        self.cpp_info.requires = ["aws-c-common::aws-c-common", "aws-c-cal::aws-c-cal"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl", "rt"]
