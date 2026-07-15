#!/usr/bin/env python3
"""Conan recipe for pdfcrack 0.21 — PDF password recovery tool.

pdfcrack is a simple tool for recovering passwords from PDF documents.
It uses a plain Makefile (no configure, no install target). Patches add
a dummy configure script and an install target for conan compatibility.
"""
import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PdfcrackConan(ConanFile):
    name = "pdfcrack"
    version = "0.21"
    description = "PDF password recovery tool for recovering passwords from PDF documents"
    license = "GPL-2.0-or-later"
    homepage = "https://pdfcrack.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # pdfcrack has no external dependencies

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cc(self):
        # R33: Get compiler from Conan conf, not undefined shell variables
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp_execs.get("c") or "clang"

    def _is_ohos(self):
        return self.settings.os == "OHOS"

    def _sign_elf(self, path, src):
        """Sign ELF binary on OHOS for execution on HarmonyOS."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if Path(sign_tool).exists():
            # .codesign section may not exist on unsigned binaries, so ignore failure
            self.run(f"{objcopy} --remove-section .codesign {path} || true", cwd=src)
            self.run(f"{sign_tool} sign -inFile {path} "
                     f"-outFile {path}.signed -selfSign 1", cwd=src)
            shutil.move(f"{path}.signed", path)
        os.chmod(path, 0o755)

    def build(self):
        apply_conandata_patches(self)

        cc = self._get_cc()
        src = self.source_folder

        # R9: Always use -j1
        # R33: Use CC from Conan conf, not shell env
        # The patches add a dummy configure script and install target
        self.run(f"./configure --prefix={self.package_folder}", cwd=src)
        self.run(f"make CC={cc} -j1", cwd=src)

        # Sign the ELF binary on OHOS
        if self._is_ohos():
            self._sign_elf(f"{src}/pdfcrack", src)

    def package(self):
        # Copy the pdfcrack binary to bin/
        copy(self, "pdfcrack", self.source_folder, os.path.join(self.package_folder, "bin"))
        os.chmod(os.path.join(self.package_folder, "bin", "pdfcrack"), 0o755)

    def package_info(self):
        self.cpp_info.libs = []  # pdfcrack is a command-line tool, not a library
        self.cpp_info.bindirs = ["bin"]
