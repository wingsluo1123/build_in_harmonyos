#!/usr/bin/env python3
"""Conan recipe for massdns 1.1.0 — high-performance DNS stub resolver.

MassDNS is a simple high-performance DNS stub resolver targeting those who
seek to resolve a massive amount of domain names. It is a command-line tool
built with a plain Makefile (no configure script).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MassdnsConan(ConanFile):
    name = "massdns"
    version = "1.1.0"
    description = "High-performance DNS stub resolver for batch DNS resolution"
    license = "GPL-3.0"
    homepage = "https://github.com/blechschmidt/massdns"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        # R32: OHOS must be matched alongside Linux
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"massdns supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_c(self):
        # R33: take the compiler from the Conan profile, never from ${CC}.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return executables.get("c") or "clang"

    def generate(self):
        env = Environment()
        env.define("CC", self._compiler_c())
        env.vars(self).save_script("conanbuild_cc")

    def build(self):
        apply_conandata_patches(self)
        # R33: pass CC explicitly from Conan profile to avoid relying on
        # bare shell variables that may be empty on release workers.
        cc = self._compiler_c()
        # R9: Always use -j1 (HMDFS does not support mkfifo)
        self.run(f'make -C {self.source_folder} CC="{cc}" -j1')

    def package(self):
        # massdns produces a single binary in {source_folder}/bin/
        copy(self, "massdns", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        # Man page
        copy(self, "massdns.1", src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        # Application — no libraries, just a binary in bin/
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
