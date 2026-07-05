#!/usr/bin/env python3
"""Conan recipe template — Meson projects.

Usage: Replace Bubblewrap, bubblewrap, 0.11.0, bubblewrap 0.11.0, MIT,
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: default_library=static for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class BubblewrapConan(ConanFile):
    name = "bubblewrap"
    version = "0.11.0"
    description = "bubblewrap 0.11.0"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # libcap is system library on OHOS

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.project_options["default_library"] = "static"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        hnp_bin = "/data/service/hnp/bin"
        if hnp_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = hnp_bin + ":" + os.environ.get("PATH", "")
        os.environ["AR"] = "/data/service/hnp/bin/llvm-ar"
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        # bubblewrap is a tool (executable), not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
