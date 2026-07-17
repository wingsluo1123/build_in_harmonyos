#!/usr/bin/env python3
"""Conan recipe — open-adventure 1.20 (Makefile)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class OpenAdventureConan(ConanFile):
    name = "open-adventure"
    version = "1.20"
    description = "Colossal Cave Adventure — the classic text adventure game"
    license = "BSD-2-Clause"
    homepage = "https://gitlab.com/esr/open-adventure"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libedit/20240808")
        self.requires("ncurses/6.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        cc = self.conf.get("tools.build:compiler_executables:c", "clang", check_type=str)

        # PkgConfigDeps generates .pc files in the build folder;
        # the Makefile uses pkg-config --cflags libedit for include paths
        env = {"PKG_CONFIG_PATH": self.build_folder}
        self.run(f'make CC={cc} CFLAGS="-fPIC -O2" LIBS="-ledit -lncurses" -j1', env=env)
        self.run(f'make cheat CC={cc} CFLAGS="-fPIC -O2" LIBS="-ledit -lncurses"', env=env)

    def package(self):
        copy(self, "advent", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "cheat", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
