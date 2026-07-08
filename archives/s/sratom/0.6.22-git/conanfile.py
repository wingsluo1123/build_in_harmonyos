#!/usr/bin/env python3
"""Conan recipe for sratom — Meson-based LV2 data serialization library."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu.pkgconfigdeps import PkgConfigDeps
from conan.tools.layout import basic_layout


class SratomConan(ConanFile):
    name = "sratom"
    version = "0.6.22-git"
    description = "C library for serializing LV2 data to RDF/Turtle"
    license = "ISC"
    homepage = "https://drobilla.net/software/sratom"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lv2/1.18.11-git")
        self.requires("serd/0.32.9-git")
        self.requires("sord/0.16.22-git")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "static"
        tc.generate()
        pkg = PkgConfigDeps(self)
        pkg.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "sratom-0")
        self.cpp_info.libs = ["sratom-0"]
        self.cpp_info.includedirs = ["include/sratom-0"]
