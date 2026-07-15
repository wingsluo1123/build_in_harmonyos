#!/usr/bin/env python3
"""Conan recipe for ipcalc 1.0.3 — IPv4/IPv6 address calculator tool.

ipcalc takes an IP address and netmask and calculates the resulting
broadcast, network, Cisco wildcard mask, and host range for both IPv4
and IPv6. It also supports network deaggregation.

Source: https://gitlab.com/ipcalc/ipcalc
License: GPLv2
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class IpcalcConan(ConanFile):
    name = "ipcalc"
    version = "1.0.3"
    description = "Modern IPv4/IPv6 address calculator tool"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.com/ipcalc/ipcalc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, not shell env
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # Build without optional GeoIP/MaxMind dependencies
        self.run(
            f'make -C {self.source_folder} '
            f'USE_GEOIP=no USE_MAXMIND=no '
            f'CC={cc} '
            f'CFLAGS="-fPIC -O2 -Wall -DVERSION=\\"{self.version}\\"" '
            f'-j1'
        )

    def package(self):
        # Install binary and man page manually (Makefile has no install target)
        copy(self, "ipcalc", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "ipcalc.1.md", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
