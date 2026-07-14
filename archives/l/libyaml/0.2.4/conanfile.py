#!/usr/bin/env python3
"""Conan recipe for libyaml 0.2.4 — CMake build.
Source: GitHub archive (has CMakeLists.txt + cmake/config.h.in).
"""
from conan import ConanFile
from conan.tools.files import get
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibyamlConan(ConanFile):
    name = "libyaml"
    version = "0.2.4"
    description = "YAML parser/emitter library"
    license = "MIT"
    homepage = "https://pyyaml.org/wiki/LibYAML"
    url = ""
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["yaml"]
