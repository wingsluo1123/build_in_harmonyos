#!/usr/bin/env python3
"""Conan recipe — crosstool-ng 1.28.0 (Autotools application).

crosstool-ng is a versatile (cross) toolchain generator that provides
the `ct-ng` command-line tool.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CrosstoolNgConan(ConanFile):
    name = "crosstool-ng"
    version = "1.28.0"
    description = "Crosstool-NG is a versatile (cross) toolchain generator"
    license = "MIT"
    homepage = "https://crosstool-ng.github.io/"
    url = ""  # CI fills this

    package_type = "application"

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
        tc = AutotoolsToolchain(self)
        # crosstool-ng needs ncurses headers and library
        # ncurses is installed as system prebuilt package at $HOME/usr/local
        home = os.environ.get("HOME", "/storage/Users/currentUser")
        tc.cflags.append(f"-I{home}/usr/local/include")
        tc.ldflags.append(f"-L{home}/usr/local/lib")
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
        # ct-ng is a command-line tool, expose bin directory
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib", "share/crosstool-ng/lib"]
        self.cpp_info.resdirs = ["share/crosstool-ng"]
