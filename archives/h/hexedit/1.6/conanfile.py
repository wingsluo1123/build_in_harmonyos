#!/usr/bin/env python3
"""Conan recipe for hexedit 1.6 (console hex file editor)."""

import os
import shutil

from conan import ConanFile
from conan.tools.files import get, replace_in_file, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain


class HexeditConan(ConanFile):
    name = "hexedit"
    version = "1.6"
    package_type = "application"

    description = "View and edit files in hex"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/pixel/hexedit"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # Copy the configure script (patches/0001-configure.patch is a full configure,
        # not a diff — needed because GitHub source doesn't include configure).
        copy(self, "patches/0001-configure.patch", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        self.requires("ncurses/6.4")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # GitHub source does not include a pre-generated configure script.
        # Copy the one from patches/ (generated from configure.ac via autoconf).
        shutil.copy(
            os.path.join(self.recipe_folder, "patches", "0001-configure.patch"),
            os.path.join(self.source_folder, "configure"),
        )
        os.chmod(os.path.join(self.source_folder, "configure"), 0o755)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "HELP2MAN=/bin/true",
            "LIBS=-lncursesw",
        ])
        tc.generate()

    def build(self):
        # Apply platform patches for HMDFS cross-compilation
        replace_in_file(self, self.source_folder + "/configure",
                        "cross_compiling=no", "cross_compiling=maybe")
        replace_in_file(self, self.source_folder + "/configure",
                        "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make("-j1")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []