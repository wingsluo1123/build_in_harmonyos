#!/usr/bin/env python3
"""Conan recipe for btop 1.4.7 — a resource monitor and process manager (C++17, terminal UI)."""

import os

from conan import ConanFile
from conan.tools.files import copy, get, export_conandata_patches, apply_conandata_patches


class BtopConan(ConanFile):
    name = "btop"
    package_type = "application"
    version = "1.4.7"
    license = "Apache-2.0"
    homepage = "https://github.com/aristocratos/btop"
    url = "https://github.com/aristocratos/btop"
    description = "A resource monitor and process manager (C++17, terminal UI)"
    topics = ("monitor", "process", "terminal", "tui")

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        # Access the dict form: tools.build:compiler_executables then .get("cxx")
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cxx", "clang++")
        cxxflags = self.conf.get("tools.build:cxxflags", default="", check_type=str)
        # R9: Use -j1; run make in the source folder; quote CXXFLAGS for spaces.
        self.run(f'make -C "{self.source_folder}" -j1 CXX="{cxx}" CXXFLAGS="{cxxflags}"')

    def package(self):
        copy(self, "btop", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
