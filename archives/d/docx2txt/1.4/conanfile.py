#!/usr/bin/env python3
"""Conan recipe — docx2txt 1.4 (Makefile/Perl script tool)"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Docx2TxtConan(ConanFile):
    name = "docx2txt"
    version = "1.4"
    description = "从 DOCX 文件提取纯文本的 Perl 脚本工具"
    license = "GPL-3.0-or-later"
    homepage = "https://sourceforge.net/projects/docx2txt/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "docx2txt.pl", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "docx2txt.sh", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "docx2txt.config", self.source_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]
