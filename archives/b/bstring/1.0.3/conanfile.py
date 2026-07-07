#!/usr/bin/env python3
"""Conan recipe for bstring — better string library for C.

Build system: Meson
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class BstringConan(ConanFile):
    name = "bstring"
    version = "1.0.3"
    description = "Better string library for C"
    license = "MIT"
    homepage = ""
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

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "static"
        tc.generate()
        # Fix: meson can't find llvm-ar, add toolchain bin to PATH
        hnp_bin = "/data/service/hnp/bin"
        if hnp_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = hnp_bin + ":" + os.environ.get("PATH", "")
        os.environ["AR"] = "/data/service/hnp/bin/llvm-ar"

    def build(self):
        apply_conandata_patches(self)
        # Fix: meson can't find llvm-ar, add toolchain bin to PATH
        hnp_bin = "/data/service/hnp/bin"
        if hnp_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = hnp_bin + ":" + os.environ.get("PATH", "")
        os.environ["AR"] = "/data/service/hnp/bin/llvm-ar"
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["bstring"]
