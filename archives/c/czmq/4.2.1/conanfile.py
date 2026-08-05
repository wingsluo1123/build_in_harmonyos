#!/usr/bin/env python3
"""Conan recipe for czmq 4.2.1 — High-level C binding for ZeroMQ."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CzmqConan(ConanFile):
    name = "czmq"
    version = "4.2.1"
    description = "High-level C binding for ZeroMQ, providing sockets, actors, and security"
    license = "MPL-2.0"
    homepage = "https://github.com/zeromq/czmq"
    url = "https://github.com/zeromq/czmq"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zeromq/4.3.5")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CZMQ_BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["CZMQ_BUILD_STATIC"] = "OFF" if self.options.shared else "ON"
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
        self.cpp_info.libs = ["czmq"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
