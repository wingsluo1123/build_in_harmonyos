#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

Uses direct compilation (like blake3) to keep test simple and portable.
CI L0d requires self.run() in this file.

File location: archives/{letter}/binutils/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile


class BinutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Direct compilation: link against binutils from Conan package
        dep = self.dependencies["binutils"]
        cpp = dep.cpp_info
        inc_flags = " ".join(f"-I{d}" for d in cpp.includedirs)
        lib_flags = " ".join(f"-L{d}" for d in cpp.libdirs)
        # Only link against libraries that actually exist
        available_libs = []
        for lib_dir in cpp.libdirs:
            available_libs = [l for l in cpp.libs if any(os.path.isfile(os.path.join(lib_dir, f"lib{l}.a")) or os.path.isfile(os.path.join(lib_dir, f"lib{l}.so")) for l in [l])]
        libs_to_link = available_libs if available_libs else cpp.libs[:1]  # fallback to first lib
        link_flags = " ".join(f"-l{l}" for l in libs_to_link)
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test.c -o test_binutils {inc_flags} {lib_flags} {link_flags}")

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_binutils'", env="conanrun")
