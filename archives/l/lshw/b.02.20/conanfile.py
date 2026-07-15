#!/usr/bin/env python3
"""Conan recipe for lshw B.02.20 — Hardware Lister for Linux.

lshw is a small command-line tool that provides detailed information
on the hardware configuration of the machine. It uses a simple Makefile
(no configure script) and has no external dependencies (SQLite and ZLIB
support are disabled by default).

Patches:
  0001: Add -DNONLS to DEFINES in src/Makefile (disable NLS/gettext)
  0002: Add #include "config.h" to src/core/pnp.cc (fix missing include)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv


class LshwConan(ConanFile):
    name = "lshw"
    version = "b.02.20"
    description = "Hardware Lister — provides detailed hardware configuration information"
    license = "GPL-2.0"
    homepage = "https://github.com/lyonel/lshw"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # lshw is a CLI tool, not a library
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R32: settings.os must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lshw only supports Linux/OHOS, got {self.settings.os}"
            )
        env = VirtualBuildEnv(self)
        env.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, not from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        # R9: Always use -j1
        self.run(
            f'make -C src CXX="{cxx}" VERSION={self.version} '
            f'PREFIX=/usr/local -j1',
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package(self):
        self.run(
            f"make -C src install "
            f"SBINDIR=/bin MANDIR=/share/man DATADIR=/share/lshw "
            f"DESTDIR={self.package_folder}",
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package_info(self):
        # lshw is a CLI tool — binary in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
