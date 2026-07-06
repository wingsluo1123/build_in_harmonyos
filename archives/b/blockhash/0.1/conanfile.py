#!/usr/bin/env python3
"""Conan recipe — Custom build (single C file compilation).

blockhash is a perceptual image hash calculation tool.
Uses stb_image.h (embedded) instead of MagickWand for HarmonyOS compatibility.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BlockhashConan(ConanFile):
    name = "blockhash"
    version = "0.1"
    description = "Perceptual image hash calculation tool based on Block Mean Value algorithm"
    license = "MIT"
    homepage = "https://github.com/commonsmachinery/blockhash"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # stb_image is embedded, no external dependency

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Provide stb_image.h for the patched source
        stb_path = '/storage/Users/currentUser/tmp/stb_image.h'
        if os.path.isfile(stb_path):
            copy(self, 'stb_image.h', os.path.dirname(stb_path), self.source_folder)
        # blockhash is a single C file, compiled directly with stb_image.h
        build_dir = os.path.join(self.build_folder, "build")
        if not os.path.exists(build_dir):
            os.makedirs(build_dir)
        self.run(
            "clang -O3 -DVERSION='\"0.3.2-harmonyos\"' "
            f"-I{self.source_folder} "
            f"-o {os.path.join(build_dir, 'blockhash')} "
            f"{os.path.join(self.source_folder, 'blockhash.c')} -lm",
            env="conanrun"
        )

    def package(self):
        copy(self, "blockhash",
             os.path.join(self.build_folder, "build"),
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
