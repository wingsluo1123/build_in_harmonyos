#!/usr/bin/env python3
"""Conan recipe — dynamips 0.2.23 (CMake)

dynamips is a Cisco router emulation platform. On aarch64, JIT is not
available so DYNAMIPS_ARCH=nojit is used. libelf is a required system
dependency (find_package(LibElf)). libpcap is optional.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DynamipsConan(ConanFile):
    name = "dynamips"
    version = "0.2.23"
    description = "Cisco router emulation platform"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/GNS3/dynamips"
    url = "https://cnb.cool/ohpcd/ohos-pc-archives/-/tree/main/archives/d/dynamips/0.2.23"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["DYNAMIPS_ARCH"] = "nojit"
        tc.variables["ANY_COMPILER"] = "1"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
