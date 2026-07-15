#!/usr/bin/env python3
"""Conan recipe for microsocks — a tiny SOCKS5 server.

microsocks is a command-line application (not a library). It uses a simple
Makefile build system. The Makefile does `-include config.mak` to pick up
the prefix, so we generate config.mak directly in build().
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, save, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class MicrosocksConan(ConanFile):
    name = "microsocks"
    version = "1.0.5"
    description = "tiny, portable SOCKS5 server with very moderate resource usage"
    license = "MIT"
    homepage = "https://github.com/rofl0r/microsocks"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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

        # microsocks Makefile does `-include config.mak` to pick up prefix
        # Generate config.mak in the source folder (where Makefile lives)
        config_mak = f"prefix = {self.package_folder}\n"
        save(self, os.path.join(self.source_folder, "config.mak"), config_mak)

        # R33: Get compiler from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")

        # Run make in the source folder (where Makefile is)
        self.run(f"make -C {self.source_folder} CC={cc} -j1")

    def package(self):
        # microsocks produces a single binary
        copy(self, "microsocks", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
