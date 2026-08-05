#!/usr/bin/env python3
"""Conan recipe -- libid3tag 0.16.3 (ID3 tag parser library).

libid3tag is a C library for parsing and manipulating ID3 tags
(metadata in MP3 audio files). Supports ID3v1 and ID3v2 formats.

Build system: CMake
License: GPL-2.0-or-later
"""
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
    url = ""  # CI fills this

    settings = "os", "arch", "compiler", "build_type"
    package_type = "library"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {
        "shared": True,
        "fPIC": True,
        "zlib/*:fPIC": True,
    }
    generators = "CMakeDeps"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported"
            )

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("zlib/1.3.1.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x dropped compatibility with cmake_minimum_required < 3.5.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        # --- Patch CMakeLists.txt for Conan/CMake 4.x compatibility ---
        cmakefile = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(cmakefile, "r") as f:
            content = f.read()

        # 1) CMake 4.x rejects cmake_minimum_required(VERSION 3.1.0).
        #    The toolchain cache variable is not visible yet because
        #    cmake_minimum_required() runs before project() which loads
        #    the toolchain. Raise the minimum version to 3.5.
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
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYRIGHT", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["id3tag"]
        self.cpp_info.set_property("cmake_file_name", "id3tag")
        self.cpp_info.set_property("cmake_target_name", "id3tag::id3tag")
        self.cpp_info.set_property("pkg_config_name", "id3tag")
