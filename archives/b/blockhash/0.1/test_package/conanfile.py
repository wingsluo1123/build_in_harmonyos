#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

Uses direct compilation (like blake3) to keep test simple and portable.
CI L0d requires self.run() in this file.

File location: archives/{letter}/blockhash/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile


class BlockhashTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Direct compilation: link against blockhash from Conan package
        dep = self.dependencies["blockhash"]
        cpp = dep.cpp_info
        inc_flags = " ".join(f"-I{d}" for d in cpp.includedirs)
        lib_flags = " ".join(f"-L{d}" for d in cpp.libdirs)
        link_flags = " ".join(f"-l{l}" for l in cpp.libs)
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test.c -o test_blockhash {inc_flags} {lib_flags} {link_flags}")

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_blockhash'", env="conanrun")
