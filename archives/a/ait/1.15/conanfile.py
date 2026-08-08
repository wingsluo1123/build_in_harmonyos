#!/usr/bin/env python3
"""Conan recipe — ait 1.15 (Emacs-style editor, C/Makefile).

ait is a small GNU Emacs style editor written in C, depending only on
libc. Build: make CC=clang CFLAGS=... LDFLAGS=... ait.

R38: ait is a command-line tool → commands.json declared at software level.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches


class AitConan(ConanFile):
    name = "ait"
    version = "1.15"
    description = "Small yet mighty GNU Emacs style editor"
    license = "BSD-3-Clause"
    homepage = "https://ftp.netbsd.org/pub/NetBSD/misc/ktnb/"
    url = "https://ftp.netbsd.org/pub/NetBSD/misc/ktnb/ait-1.15.tar.gz"

    package_type = "application"
    settings = "os", "arch", "build_type"

    # Export patches declared in conandata.yml (none currently).
    def export_sources(self):
        pass

    def layout(self):
        # Source unpacked into self.source_folder.
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # ait uses a simple Makefile; no configure script.
        # CC/CFLAGS/LDFLAGS are passed via make variables (R33: explicit, not shell env).
        self.run("make clean CC=clang", cwd=self.source_folder)
        self.run(
            'make ait CC=clang CFLAGS="-fPIC -O2 -Wall" LDFLAGS=""',
            cwd=self.source_folder,
        )

    def package(self):
        # Install the binary into bin/.
        copy(
            self,
            "ait",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )

    def package_info(self):
        # Application: expose bin/ so consumers can run ait.
        self.cpp_info.bindirs = ["bin"]
