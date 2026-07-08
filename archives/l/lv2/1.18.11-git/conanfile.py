#!/usr/bin/env python3
"""Conan recipe for lv2 — LV2 audio plugin specification (header-only)."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class Lv2Conan(ConanFile):
    name = "lv2"
    version = "1.18.11-git"
    description = "LV2 audio plugin specification - headers and specification files for LV2 plugins"
    license = "ISC"
    homepage = "https://lv2plug.in"
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

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "lv2")
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
