#!/usr/bin/env python3
"""Conan recipe for libwapcaplet — NetSurf string internment library."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibwapcapletConan(ConanFile):
    name = "libwapcaplet"
    version = "0.4.3"
    description = "String internment library from the NetSurf project"
    license = "MIT"
    homepage = "https://www.netsurf-browser.org/projects/libwapcaplet/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

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

        # Get compiler from Conan conf dict (R33: don't use shell env vars)
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c", "clang") if compilers else "clang"

        # Build static library using standalone Makefile
        # Must run in source_folder where Makefile lives
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        # Install directly to package folder
        self.run(f"make install PREFIX={self.package_folder}", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["wapcaplet"]
        self.cpp_info.includedirs = ["include"]
