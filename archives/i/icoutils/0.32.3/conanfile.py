#!/usr/bin/env python3
"""Conan recipe — icoutils 0.32.3 (autotools)

icoutils is a set of command-line tools for extracting and converting
Microsoft Windows icon and cursor resources (ICO/CUR/ANI).
Produced binaries: icotool, wrestool, extresso, genresscript
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IcoutilsConan(ConanFile):
    name = "icoutils"
    version = "0.32.3"
    description = "Extract and convert Windows icon and cursor resources (ICO/CUR/ANI)"
    license = "GPL-3.0"
    homepage = "https://www.nongnu.org/icoutils/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpng/1.6.58")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
