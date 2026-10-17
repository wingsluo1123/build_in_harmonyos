#!/usr/bin/env python3
"""Conan recipe — libproxyprotocol 1.3.3.

ANSI C library to parse and create PROXY protocol v1/v2 headers.
Build system: plain Makefile (no configure script). Produces a shared library
libs/libproxyprotocol.so plus an upstream test binary and an example.
License: LGPL-3.0 (see COPYING.LESSER in the upstream tarball).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class LibproxyprotocolConan(ConanFile):
    name = "libproxyprotocol"
    version = "1.3.3"
    description = "ANSI C library to parse and create PROXY protocol v1 and v2 headers"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/kosmas-valianos/libproxyprotocol"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf (never bare shell env vars)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # R9: -j1 deterministic build for old single-file Makefile projects
        # 'build' 目标先执行 libs_dir (mkdir -p libs) 再编 .so，直指 .so 目标会跳过 mkdir
        self.run(f"make CC={cc} -j1 build", cwd=self.source_folder)
        # R51: actually run the upstream test suite (builds + executes tests/test_libproxyprotocol)
        self.run(f"make CC={cc} -j1 tests", cwd=self.source_folder)

    def package(self):
        # Upstream Makefile has no install target; copy artifacts manually.
        # copy() 保留相对子路径，需以子目录为 src、文件名为 pattern 展平到 lib/ 与 include/
        copy(self, "libproxyprotocol.so", src=os.path.join(self.source_folder, "libs"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "proxy_protocol.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["proxyprotocol"]