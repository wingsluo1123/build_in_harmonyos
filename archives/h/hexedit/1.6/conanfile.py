#!/usr/bin/env python3
"""Conan recipe for hexedit 1.6 (console hex file editor)."""

from conan import ConanFile
from conan.tools.files import get, replace_in_file
import os


class HexeditRecipe(ConanFile):
    name = "hexedit"
    version = "1.6"
    package_type = "application"

    description = "View and edit files in hex"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/pixel/hexedit"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("hex", "editor", "terminal")

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def requirements(self):
        self.requires("ncurses/6.4")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        prefix = os.environ.get("DEFAULT_PREFIX", self.package_folder)
        configure = self.source_folder + "/configure"
        replace_in_file(self, configure, "cross_compiling=no", "cross_compiling=maybe")
        replace_in_file(self, configure, "umask 077", "umask 022")
        self.run(
            "./configure --prefix=" + prefix
            + " HELP2MAN=/bin/true"
            + " CFLAGS='-fPIC -O2 -I" + prefix + "/include'"
            + " LDFLAGS='-L" + prefix + "/lib'"
            + " LIBS='-lncursesw'",
            cwd=self.source_folder
        )
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        self.run("make install DESTDIR=" + self.package_folder, cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []