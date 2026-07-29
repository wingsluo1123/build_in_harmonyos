#!/usr/bin/env python3
"""Conan recipe - libsndfile 1.2.2 (CMake)."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class LibsndfileConan(ConanFile):
    name = "libsndfile"
    version = "1.2.2"
    description = "C library for reading and writing sampled audio files"
    license = "LGPL-2.1-or-later"
    homepage = "https://libsndfile.github.io/libsndfile/"
    url = "https://github.com/libsndfile/libsndfile"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_PROGRAMS"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_REGTEST"] = False
        tc.variables["ENABLE_EXTERNAL_LIBS"] = False
        tc.variables["ENABLE_MPEG"] = False
        tc.variables["ENABLE_EXPERIMENTAL"] = False
        tc.variables["INSTALL_MANPAGES"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["sndfile"]
        self.cpp_info.set_property("cmake_file_name", "SndFile")
        self.cpp_info.set_property("cmake_target_name", "SndFile::sndfile")
        self.cpp_info.set_property("pkg_config_name", "sndfile")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
