#!/usr/bin/env python3
"""Conan recipe for zeromq 4.3.5 — High-performance asynchronous messaging library."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ZeromqConan(ConanFile):
    name = "zeromq"
    version = "4.3.5"
    description = "High-performance asynchronous messaging library for distributed systems"
    license = "MPL-2.0"
    homepage = "https://zeromq.org/"
    url = "https://github.com/zeromq/libzmq"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED"] = "ON"
        tc.variables["BUILD_STATIC"] = "ON"
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.variables["ENABLE_DRAFTS"] = "OFF"
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
        self.cpp_info.libs = ["zmq"]
        self.cpp_info.includedirs = ["include"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "rt"]
