#!/usr/bin/env python3
"""Conan recipe — blockhash 0.1 (custom build, stb_image vendored)"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout
import os


class BlockhashConan(ConanFile):
    name = "blockhash"
    version = "0.1"
    description = "Perceptual image hash calculation tool based on Block Mean Value algorithm"
    license = "MIT"
    homepage = "https://github.com/commonsmachinery/blockhash"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "stb_image.h"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Copy vendored stb_image.h to source directory
        copy(self, "stb_image.h", self.export_sources_folder, self.source_folder)
        # Get compiler from Conan configuration (R33: no bare shell variables)
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c", "clang")
        # Set optimization flags based on build_type
        bt = str(self.settings.build_type)
        if bt == "Debug":
            cflags = "-g -O0"
        elif bt == "RelWithDebInfo":
            cflags = "-g -O2"
        elif bt == "MinSizeRel":
            cflags = "-Os"
        else:
            cflags = "-O3"
        self.run(f'"{cc}" {cflags} -o blockhash blockhash.c -lm', cwd=self.source_folder)

    def package(self):
        copy(self, "blockhash", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
