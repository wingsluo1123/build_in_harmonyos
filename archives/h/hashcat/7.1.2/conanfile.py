#!/usr/bin/env python3
"""Conan recipe for hashcat 7.1.2 — high-performance password recovery tool.

hashcat uses a custom Makefile build system (not autotools/cmake).
Patches add HarmonyOS platform support:
  - 0001: Replace getpass() with fgets() for OHOS
  - 0002: Add HarmonyOS OS detection, compiler settings, and CFLAGS to Makefile
  - 0003: Disable CPU affinity (pthread_setaffinity_np not available on OHOS)
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class HashcatConan(ConanFile):
    name = "hashcat"
    version = "7.1.2"
    description = "High-performance password recovery tool supporting 300+ hash algorithms"
    license = "MIT"
    homepage = "https://hashcat.net/hashcat/"
    url = "https://github.com/hashcat/hashcat"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # hashcat has no external Conan dependencies

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cc(self):
        # R33: Get compiler from Conan conf, not shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp_execs.get("c") or "clang"

    def _get_cxx(self):
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp_execs.get("cpp") or "clang++"

    def _get_python_cflags(self):
        """Detect Python include path for Python bridge plugin."""
        try:
            import sysconfig
            inc = sysconfig.get_path("include")
            if inc and Path(inc).exists() and (Path(inc) / "Python.h").exists():
                return f"-I{inc}"
        except Exception:
            pass
        return ""

    def build(self):
        apply_conandata_patches(self)

        cc = self._get_cc()
        cxx = self._get_cxx()
        python_cflags = self._get_python_cflags()

        # Always -j1 (HMDFS doesn't support FIFO for make jobserver)
        make_args = [
            f"CC={cc}",
            f"CXX={cxx}",
            "-j1",
        ]
        if python_cflags:
            make_args.append(f"PYTHON_CFLAGS={python_cflags}")

        self.run("make " + " ".join(make_args), cwd=self.source_folder)

    def package(self):
        # Copy hashcat binary
        copy(self, "hashcat", self.source_folder, os.path.join(self.package_folder, "bin"))

        # Copy runtime data: modules, OpenCL kernels, bridges
        for dir_name in ["modules", "OpenCL", "bridges"]:
            src_dir = os.path.join(self.source_folder, dir_name)
            if os.path.isdir(src_dir):
                copy(self, "*", src_dir,
                     os.path.join(self.package_folder, "share", "hashcat", dir_name))

    def package_info(self):
        self.cpp_info.libs = []  # hashcat is a binary tool, not a library
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
