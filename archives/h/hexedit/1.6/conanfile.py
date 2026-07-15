#!/usr/bin/env python3
"""Conan recipe for hexedit 1.6 (console hex file editor)."""

from conan import ConanFile
from conan.tools.files import get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain


class HexeditConan(ConanFile):
    name = "hexedit"
    version = "1.6"
    package_type = "application"

    description = "View and edit files in hex"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/pixel/hexedit"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "HELP2MAN=/bin/true",
            "LIBS=-lncursesw",
        ])
        tc.generate()

    def build(self):
        # Generate configure script from configure.ac
        self.run("autoconf", cwd=self.source_folder)
        # Apply platform patches for HMDFS
        replace_in_file(self, self.source_folder + "/configure", "cross_compiling=no", "cross_compiling=maybe")
        replace_in_file(self, self.source_folder + "/configure", "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make("-j1")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []