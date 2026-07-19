#!/usr/bin/env python3
"""Conan recipe — ncurses 6.4 (terminal control library).

ncurses is a library for controlling the terminal display.
Built statically with wide-character support (--enable-widec).
The shared-library build is deliberately disabled to avoid
interfering with the system's libncursesw.so.6.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NcursesConan(ConanFile):
    name = "ncurses"
    version = "6.4"
    description = "ncurses (new curses) library — terminal control"
    license = "MIT"
    homepage = "https://invisible-island.net/ncurses/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

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
        # Static build only — see manifest.yaml notes
        tc.configure_args.append("--without-shared")
        tc.configure_args.append("--without-debug")
        tc.configure_args.append("--without-ada")
        tc.configure_args.append("--without-manpages")
        tc.configure_args.append("--without-tests")
        tc.configure_args.append("--without-cxx-binding")
        tc.configure_args.append("--enable-widec")
        tc.configure_args.append("--enable-overwrite")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Remove unneeded items (terminfo data is large; keep it)
        copy(self, "lib/*.a",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Wide-character build: all libraries have the 'w' suffix
        self.cpp_info.libs = ["ncursesw", "panelw", "menuw", "formw"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]