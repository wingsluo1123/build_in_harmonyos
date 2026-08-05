#!/usr/bin/env python3
"""Conan recipe -- libid3tag 0.16.3 (ID3 tag parser library)."""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy

class Libid3tagConan(ConanFile):
    name = "libid3tag"
    version = "0.16.3"
    description = "ID3 tag parser and manipulation library"
    license = "GPL-2.0-or-later"
    homepage = "https://download.savannah.nongnu.org/releases/libid3tag/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"
    package_type = "library"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True, "zlib/*:fPIC": True}
    generators = "CMakeDeps"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("zlib/1.3.1.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmakefile = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(cmakefile, "r") as f:
            content = f.read()
        content = content.replace(
            "cmake_minimum_required(VERSION 3.1.0)",
            "cmake_minimum_required(VERSION 3.5)"
        )
        with open(cmakefile, "w") as f:
            f.write(content)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYRIGHT", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["id3tag"]
        self.cpp_info.set_property("cmake_file_name", "id3tag")
        self.cpp_info.set_property("cmake_target_name", "id3tag::id3tag")
        self.cpp_info.set_property("pkg_config_name", "id3tag")
