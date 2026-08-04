#!/usr/bin/env python3
"""Conan recipe — alac (Apple Lossless Audio Codec), raw Makefile build."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AlacConan(ConanFile):
    name = "alac"
    version = "cci.20121212"
    description = "The Apple Lossless Audio Codec (ALAC) is a lossless audio codec developed by Apple."
    license = "Apache-2.0"
    homepage = "https://macosforge.github.io/alac"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        # The alac makefile uses CC=g++ for C++ compilation
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++")
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        # R9: Always use -j1
        # Use cxx since the makefile treats CC as the C++ compiler
        # Source is in codec/ subdirectory (repo structure)
        src_dir = os.path.join(self.source_folder, "codec")
        self.run(f"make CC={cxx} AR={ar} -j1", cwd=src_dir)

    def package(self):
        src_dir = os.path.join(self.source_folder, "codec")
        copy(self, "APPLE_LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*.h", src_dir, os.path.join(self.package_folder, "include"))
        copy(self, "*.a", src_dir, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["alac"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")