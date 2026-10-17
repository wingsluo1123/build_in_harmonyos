#!/usr/bin/env python3
"""Experimental xmbmon 2.05 native thermal backend, built with CMake."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class XmbmonConan(ConanFile):
    name = "xmbmon"
    version = "2.05"
    description = "Experimental native temperature monitor with optional HDC-assisted raw fan readings"
    license = "BSD-style custom (see CopyRight)", "Apache-2.0"
    homepage = "https://www.nt.phys.kyushu-u.ac.jp/shimizu/download/download.html"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "integration.md"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libxt/1.3.1")
        self.requires("libx11/1.8.13")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os != "OHOS" or self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("This experimental service backend is validated on OHOS armv8 only")
        if str(self.settings.compiler) != "clang" or str(self.settings.compiler.version) != "15":
            raise ConanInvalidConfiguration("The pinned system C++ ABI bridge requires the tested Clang 15 SDK")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self, generator="Unix Makefiles")
        toolchain.variables["MBMON_BACKEND"] = "thermal"
        toolchain.variables["MBMON_BUILD_GUI"] = True
        toolchain.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        toolchain.variables["CMAKE_INSTALL_BINDIR"] = "bin"
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(self, "CopyRight", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE", os.path.join(self.source_folder, "platform-headers"),
             os.path.join(self.package_folder, "licenses", "platform-headers"))
        copy(self, "PROVENANCE.json", os.path.join(self.source_folder, "platform-headers"),
             os.path.join(self.package_folder, "share", "xmbmon"))
        copy(self, "integration.md", self.export_sources_folder,
             os.path.join(self.package_folder, "share", "xmbmon"))

    def package_info(self):
        self.cpp_info.libs = ["mbmon_measurement"]
        self.cpp_info.includedirs = ["include/xmbmon"]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
