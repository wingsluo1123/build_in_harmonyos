#!/usr/bin/env python3
"""Conan recipe for unarj 2.63a — ARJ archive extraction utility.

unarj is a command-line tool for extracting ARJ archives (extraction only).
Build system: simple Makefile (no configure script).
License: GPL-2.0
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class UnarjConan(ConanFile):
    name = "unarj"
    version = "2.63a"
    description = "ARJ archive extraction utility"
    license = "GPL-2.0"
    homepage = "https://arj.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: Platform check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Use compiler from Conan profile, never from shell env vars
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = executables.get("c") or "clang"
        # R9: Always use -j1
        # CFLAGS must include -DUNIX for POSIX build path
        self.run(
            f'make CC="{cc}" CFLAGS="-fPIC -O2 -Wall -DUNIX" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "unarj", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
