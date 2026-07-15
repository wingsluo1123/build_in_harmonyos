#!/usr/bin/env python3
"""Conan recipe for hexedit 1.6 (console hex file editor)."""

import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


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

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        p = os.environ.get("DEFAULT_PREFIX", "/storage/Users/currentUser/usr/local")
        self.run(
            "bash ./configure --prefix=%s" % p
            + " HELP2MAN=/bin/true"
            + " CFLAGS='-fPIC -O2 -I%s/include'" % p
            + " LDFLAGS='-L%s/lib'" % p
            + " LIBS='-lncursesw'",
            cwd=self.source_folder
        )
        self.run("make -j$(nproc)", cwd=self.source_folder)

    def package(self):
        copy(self, "hexedit", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []