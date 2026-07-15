#!/usr/bin/env python3
"""Conan recipe — gsm 1.0.23 (Makefile)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GsmConan(ConanFile):
    name = "gsm"
    version = "1.0.23"
    description = "GSM 06.10 语音编解码库，包含 toast 压缩工具"
    license = "Industrial use OK (类似 BSD)"
    homepage = "https://www.quut.com/gsm/"
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
        # Patch sets CC=clang, CCFLAGS with -fPIC, LN=ln -s in Makefile
        self.run("make CC=clang -j1", cwd=self.source_folder)

    def package(self):
        # Headers: inc/gsm.h → include/
        copy(self, "gsm.h", os.path.join(self.source_folder, "inc"),
             os.path.join(self.package_folder, "include"))
        # Static library: lib/libgsm.a → lib/
        copy(self, "*.a", os.path.join(self.source_folder, "lib"),
             os.path.join(self.package_folder, "lib"))
        # Command-line tools: bin/toast, bin/tcat, bin/untoast → bin/
        copy(self, "toast", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "tcat", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "untoast", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["gsm"]
        self.cpp_info.bindirs = ["bin"]
