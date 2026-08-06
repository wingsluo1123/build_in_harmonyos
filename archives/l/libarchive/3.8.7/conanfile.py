#!/usr/bin/env python3
"""Conan recipe — libarchive 3.8.7 (cmake)

Multi-format archive and compression library (tar, zip, cpio, etc.).
Build system: CMake. No external dependencies required.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, collect_libs
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout


class LibarchiveConan(ConanFile):
    name = "libarchive"
    version = "3.8.7"
    description = "Multi-format archive and compression library (tar, zip, cpio, etc.)"
    license = "BSD-2-Clause"
    homepage = "https://www.libarchive.org/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_TEST"] = "OFF"
        tc.variables["ENABLE_INSTALL"] = "ON"
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
        self.cpp_info.libs = ["archive"]
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_target_name", "LibArchive::LibArchive")
        self.cpp_info.set_property("pkg_config_name", "libarchive")
