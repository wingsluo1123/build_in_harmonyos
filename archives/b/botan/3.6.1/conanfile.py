#!/usr/bin/env python3
"""Conan recipe for botan 3.6.1 — custom build system (Python configure + make).

Botan is a C++ cryptography library. It uses a custom Python-based configure
script (./configure.py) instead of autotools or cmake.

Key OHOS adaptations:
  - --os=linux: Botan doesn't recognize HarmonyOS, use Linux compatibility
  - --disable-modules=kyber*,dilithium*: These modules have compilation issues
  - explicit_bzero: Not available on OHOS, disable via post-configure patch
  - Build static library only (shared lib has runtime symbol relocation issues)
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BotanConan(ConanFile):
    name = "botan"
    version = "3.6.1"
    description = "C++ cryptography library with wide range of algorithms and protocols"
    license = "BSD-2-Clause"
    homepage = "https://botan.randombit.net"
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

        prefix = self.package_folder

        # Botan uses a Python-based configure script, not autotools
        config_cmd = (
            f"python3 ./configure.py"
            f" --prefix={prefix}"
            f" --build-tool=make"
            f" --os=linux"
            f" --cc=clang"
            f" --build-targets=static"
            f" --with-os-features=threads"
            f" --without-documentation"
            f" --disable-modules=kyber,kyber_90s,kyber_common,kyber_round3,"
            f"dilithium,dilithium_aes,dilithium_common,dilithium_round3,dilithium_shake"
        )
        self.run(config_cmd, cwd=self.source_folder)

        # Fix explicit_bzero not available on OHOS
        build_h = os.path.join(self.source_folder, "build", "include", "public", "botan", "build.h")
        if os.path.exists(build_h):
            with open(build_h, "r") as f:
                content = f.read()
            content = re.sub(
                r"#define BOTAN_TARGET_OS_HAS_EXPLICIT_BZERO",
                "/* #define BOTAN_TARGET_OS_HAS_EXPLICIT_BZERO (disabled for OHOS) */",
                content
            )
            with open(build_h, "w") as f:
                f.write(content)

        # Build static library only
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install to package folder
        self.run("make install", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["botan-3"]
        self.cpp_info.includedirs = ["include/botan-3"]
