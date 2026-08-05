#!/usr/bin/env python3
"""Conan recipe — Apache Portable Runtime (APR) 1.7.6.

Build system: autotools (configure + make).
License: Apache-2.0
Homepage: https://apr.apache.org/
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AprConan(ConanFile):
    name = "apr"
    version = "1.7.6"
    description = "Apache Portable Runtime — a C library providing a predictable and consistent interface to platform-specific features"
    license = "Apache-2.0"
    homepage = "https://apr.apache.org/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: settings.os must be Linux or OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # APR is a leaf library with no third-party dependencies
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include/apr-1"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["apr-1"]
        self.cpp_info.set_property("cmake_file_name", "apr")
        self.cpp_info.set_property("cmake_target_name", "apr::apr-1")
        self.cpp_info.set_property("pkg_config_name", "apr-1")
