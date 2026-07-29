#!/usr/bin/env python3
"""Conan recipe for SFML 2.6.1 System and Network modules."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)


class SfmlConan(ConanFile):
    name = "sfml"
    version = "2.6.1"
    description = "Simple and Fast Multimedia Library base modules"
    license = "Zlib"
    homepage = "https://www.sfml-dev.org/"
    url = "https://github.com/SFML/SFML"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["SFML_BUILD_AUDIO"] = False
        toolchain.variables["SFML_BUILD_WINDOW"] = False
        toolchain.variables["SFML_BUILD_GRAPHICS"] = False
        toolchain.variables["SFML_BUILD_NETWORK"] = True
        toolchain.variables["SFML_BUILD_EXAMPLES"] = False
        toolchain.variables["SFML_BUILD_TEST_SUITE"] = False
        toolchain.variables["SFML_BUILD_DOC"] = False
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "license.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SFML")
        library_suffix = "" if self.options.shared else "-s"

        system = self.cpp_info.components["system"]
        system.libs = [f"sfml-system{library_suffix}"]
        system.set_property("cmake_target_name", "SFML::System")
        if self.settings.os in ("Linux", "OHOS"):
            system.system_libs = ["pthread"]

        network = self.cpp_info.components["network"]
        network.libs = [f"sfml-network{library_suffix}"]
        network.requires = ["system"]
        network.set_property("cmake_target_name", "SFML::Network")
