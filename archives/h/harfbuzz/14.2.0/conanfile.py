#!/usr/bin/env python3
"""Conan recipe for harfbuzz 14.2.0 — Text shaping library (Meson)."""
import os
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches, replace_in_file
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class HarfbuzzConan(ConanFile):
    name = "harfbuzz"
    version = "14.2.0"
    description = "HarfBuzz is a text shaping library"
    license = "MIT"
    homepage = "https://harfbuzz.github.io/"
    url = "https://github.com/harfbuzz/harfbuzz"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("freetype/2.14.3")
        # glib/2.84.0 not published to remote, using system glib if available

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nofallback"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["freetype"] = "enabled"
        tc.project_options["glib"] = "enabled"
        tc.project_options["cairo"] = "disabled"
        tc.project_options["icu"] = "disabled"
        tc.project_options["coretext"] = "disabled"
        tc.project_options["directwrite"] = "disabled"
        tc.project_options["gdi"] = "disabled"
        tc.project_options["uniscribe"] = "disabled"
        tc.project_options["wasm"] = "disabled"
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["harfbuzz", "harfbuzz-subset"]
        self.cpp_info.includedirs = ["include/harfbuzz"]
        self.cpp_info.bindirs = ["bin"]