#!/usr/bin/env python3
"""Conan recipe template — Makefile projects (SCAFFOLD, AI must adjust).

⚠️  This is a SCAFFOLD only. Makefile projects vary widely — each has different
    configure scripts, build targets, output names, and install rules.
    AI MUST review and adjust every method below before use.

Typical Makefile project types:
  1. Raw make (no configure, e.g. bzip2) — build() runs make directly
  2. Makefile + configure (e.g. zlib) — build() runs ./configure first, then make

Key rules:
  - R9:  Use make -j1 (not -j$(nproc))
  - R26: System-name libs (zlib, ncurses, etc.) must be static-only
  - R5:  Use CONFIG_SHELL for configure scripts (OHOS has no /bin/sh)
  -      Set env: os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

Usage: Replace Brewcaskcompletion, brew-cask-completion, 2.1, Homebrew Cask shell补全脚本 (bash + fish), GPL-2.0, https://github.com/xyb/homebrew-cask-completion
       Fill in requires(), build commands, and cpp_info.libs as needed.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BrewcaskcompletionConan(ConanFile):
    name = "brew-cask-completion"
    version = "2.1"
    description = "Homebrew Cask shell补全脚本 (bash + fish)"
    license = "GPL-2.0"
    homepage = "https://github.com/xyb/homebrew-cask-completion"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # ⚠️ AI: Adjust the build commands below for the actual Makefile.
        #
        # If the project has a ./configure script (e.g. zlib):
        #   config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        #   self.run(f"{config_shell} ./configure --prefix=${{self.package_folder}} --static")
        #   self.run("make -j1")
        #
        # If raw make (no configure, e.g. bzip2):
        #   self.run("make CC=clang AR=llvm-ar RANLIB=llvm-ranlib -j1")

        # R9: Always use -j1, never -j$(nproc)
        # R26: For system-name libs, only build static targets
        self.run("make -j1")

    def package(self):
        # ⚠️ AI: Adjust copy patterns for actual build outputs.
        # Library name may differ from package name (e.g. zlib → libz.a)
        copy(self, "*.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "*.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        # copy(self, "brew-cask-completion", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # ⚠️ AI: Set the correct library name (e.g. "z" not "zlib" for zlib)
        self.cpp_info.libs = ["brew-cask-completion"]
