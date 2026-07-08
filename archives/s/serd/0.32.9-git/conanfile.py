#!/usr/bin/env python3
"""Conan recipe for serd — Meson-based RDF library."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class SerdConan(ConanFile):
    name = "serd"
    version = "0.32.9-git"
    description = "C library for RDF syntax reading and writing"
    license = "ISC"
    homepage = "https://drobilla.net/software/serd"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zix/0.8.1-git")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "static"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "serd-0")
        self.cpp_info.libs = ["serd-0"]
        self.cpp_info.includedirs = ["include/serd-0"]
