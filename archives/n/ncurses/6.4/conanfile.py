#!/usr/bin/env python3
"""Conan recipe for ncurses 6.4 (console UI library for OHOS aarch64)."""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class NcursesConan(ConanFile):
    name = "ncurses"
    version = "6.4"
    package_type = "library"

    description = "Free software emulation of curses in System V Release 4.0"
    license = "MIT"
    homepage = "https://invisible-island.net/ncurses/"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        vb = VirtualBuildEnv(self)
        vb.generate()

    def build(self):
        apply_conandata_patches(self)
        # ncurses uses custom configure options (--with-shared/--without-shared),
        # not the standard --enable-shared/--disable-shared. Run manually.
        configure_args = [
            "sh", os.path.join(self.source_folder, "configure"),
            "--prefix=/",
            "--without-shared",
            "--without-debug",
            "--without-ada",
            "--without-manpages",
            "--without-tests",
            "--without-cxx-binding",
            "--enable-widec",
            "--enable-overwrite",
        ]
        self.run(" ".join(configure_args), cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        self.run("make install DESTDIR=" + self.package_folder, cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["ncursesw", "panelw", "menuw", "formw"]