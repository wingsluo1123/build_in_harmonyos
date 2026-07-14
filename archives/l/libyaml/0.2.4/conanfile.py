#!/usr/bin/env python3
"""Conan recipe for libyaml 0.2.4 — CMake build."""
import os
from conan import ConanFile
from conan.tools.files import get, replace_in_file
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
        tc.generate()

    def build(self):
        # Fix cmake_minimum_required for CMake 4.x
        cm = os.path.join(self.source_folder, "CMakeLists.txt")
        if os.path.isfile(cm):
            replace_in_file(self, cm, "cmake_minimum_required(VERSION 3.0)",
                            "cmake_minimum_required(VERSION 3.5)")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["yaml"]
