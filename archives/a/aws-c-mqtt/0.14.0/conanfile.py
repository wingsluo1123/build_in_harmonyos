#!/usr/bin/env python3
"""Conan recipe for aws-c-mqtt 0.14.0 — AWS C MQTT library.

Provides MQTT 3.1.1 and MQTT 5.0 client protocol implementation.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class AwscmqttConan(ConanFile):
    name = "aws-c-mqtt"
    version = "0.14.0"
    description = "AWS C MQTT library — MQTT 3.1.1 and MQTT 5.0 client"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-mqtt"
    url = "https://github.com/awslabs/aws-c-mqtt"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aws-c-common/0.12.6")
        self.requires("aws-c-http/0.10.14")
        self.requires("aws-c-io/0.26.3")
        self.requires("aws-c-cal/0.9.13")
        self.requires("aws-c-compression/0.3.2")

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
        deps.set_property("aws-c-http", "cmake_target_name", "AWS::aws-c-http")
        deps.set_property("aws-c-io", "cmake_target_name", "AWS::aws-c-io")
        deps.set_property("aws-c-cal", "cmake_target_name", "AWS::aws-c-cal")
        deps.set_property("aws-c-compression", "cmake_target_name", "AWS::aws-c-compression")
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
        self.cpp_info.libs = ["aws-c-mqtt"]
