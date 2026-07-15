"""Conan recipe for samurai 1.2 — Ninja-compatible build tool written in C."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SamuraiConan(ConanFile):
    name = "samurai"
    version = "1.2"
    description = "Ninja-compatible build tool written in C"
    license = "Apache-2.0"
    homepage = "https://git.sr.ht/~mcf/samurai"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        compiler_executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compiler_executables.get("c", "clang")

        cflags = " ".join(filter(None, [
            "-fPIC",
            "-O2" if self.settings.build_type == "Release" else "-g",
        ]))

        # samurai uses a POSIX Makefile; ALL_CFLAGS in Makefile already
        # includes -std=c99 -Wall -Wextra -Wpedantic -Wno-unused-parameter
        self.run(f"make CC={cc} CFLAGS='{cflags}' -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "samu", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "samu.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
