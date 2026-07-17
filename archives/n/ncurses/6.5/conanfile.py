#!/usr/bin/env python3
"""Conan recipe — ncurses 6.5 (autotools)."""

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NcursesConan(ConanFile):
    name = "ncurses"
    version = "6.5"
    description = "ncurses — terminal UI library"
    license = "X11"
    homepage = "https://invisible-island.net/ncurses/"
    url = ""
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--enable-static",
                "--without-shared",
                "--without-debug",
                "--without-ada",
                "--without-manpages",
                "--without-tests",
                "--without-cxx-binding",
                "--enable-widec",
                "--enable-overwrite",
                "--enable-pc-files",
            ]
        )
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
        self.cpp_info.libs = ["ncursesw"]
        self.cpp_info.cflags = ["-D_XOPEN_SOURCE_EXTENDED"]
