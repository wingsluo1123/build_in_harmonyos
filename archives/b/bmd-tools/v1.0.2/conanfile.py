#!/usr/bin/env python3
"""Conan recipe — bmd-tools v1.0.2 (Makefile)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BmdtoolsConan(ConanFile):
    name = "bmd-tools"
    version = "v1.0.2"
    description = "Blackmagic Design USB H.264 streaming and firmware extraction tools"
    license = "GPL-2.0"
    homepage = "https://github.com/fabled/bmd-tools"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

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
        # Use system libusb
        libusb_prefix = "/storage/Users/currentUser/usr/local/libusb-package"
        cflags = f"-I{libusb_prefix}/include/libusb-1.0"
        ldflags = f"-L{libusb_prefix}/lib -lusb-1.0"
        self.run(f"make CC=clang CFLAGS='{cflags}' LDFLAGS='{ldflags}' -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "bmd-*", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "*.h", self.source_folder, os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = []
