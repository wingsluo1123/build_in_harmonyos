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

Usage: Replace Bpmtools, bpm-tools, 0.3, 音频文件节拍速度（BPM）分析工具集, GPL-2.0, http://www.pogo.org.uk/~mark/bpm-tools/
       Fill in requires(), build commands, and cpp_info.libs as needed.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BpmtoolsConan(ConanFile):
    name = "bpm-tools"
    version = "0.3"
    description = "音频文件节拍速度（BPM）分析工具集"
    license = "GPL-2.0"
    homepage = "http://www.pogo.org.uk/~mark/bpm-tools/"
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
        # bpm-tools builds executables from source
        self.run("make CC=clang -j1", cwd=self.source_folder)

    def package(self):
        # bpm-tools produces executables and scripts
        copy(self, "bpm", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "bpm-graph", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "bpm-tag", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
