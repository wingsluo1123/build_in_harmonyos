#!/usr/bin/env python3
"""Conan recipe for Boost 1.85.0 — header-only install with OpenHarmony patches.

The package installs Boost headers.  The conandata patches preserve the
OpenHarmony compatibility fixes validated with the upstream b2 test suite.
"""
import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BoostConan(ConanFile):
    name = "boost"
    version = "1.85.0"
    description = "Boost C++ Libraries 1.85.0 (header-only install with OpenHarmony patches)"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.output.info("Boost 1.85.0: header-only install with OpenHarmony patches")

    def package(self):
        # Install boost/ headers only
        copy(self, "*", src=os.path.join(self.source_folder, "boost"),
             dst=os.path.join(self.package_folder, "include", "boost"))
        copy(self, "project-config.jam", src=self.source_folder, dst=self.package_folder)
        copy(self, "user-config.jam", src=self.source_folder, dst=self.package_folder)

    def package_info(self):
        # Boost header-only: no libraries to link
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
