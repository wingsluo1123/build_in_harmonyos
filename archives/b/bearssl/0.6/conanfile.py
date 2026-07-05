#!/usr/bin/env python3
"""Conan recipe — bearssl 0.6 (custom Makefile build).

BearSSL uses a custom Makefile with CONF-based configuration files.
No configure script. Build with: make CONF=UnixClang
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BearsslConan(ConanFile):
    name = "bearssl"
    version = "0.6"
    description = "优化的 SSL/TLS 库，适用于嵌入式系统，纯 C 实现无外部依赖"
    license = "MIT"
    homepage = "https://www.bearssl.org/"
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

    def generate(self):
        pass  # BearSSL has no configure step

    def build(self):
        apply_conandata_patches(self)
        # BearSSL uses a custom Makefile with CONF-based configuration
        # UnixClang uses clang as CC/LD, which is correct for OHOS
        # Run make from source folder where the Makefile is located
        self.run(f"make -C {self.source_folder} CONF=UnixClang -j1")

    def package(self):
        src = self.source_folder
        # BearSSL with UnixClang config uses 'bclang' as BUILD directory
        build_dir = os.path.join(src, "bclang")
        # Copy static library
        copy(self, "libbearssl.a", src=build_dir, dst=os.path.join(self.package_folder, "lib"))
        # Copy brssl tool
        copy(self, "brssl", src=build_dir, dst=os.path.join(self.package_folder, "bin"))
        # Copy headers
        copy(self, "*.h", src=os.path.join(src, "inc"), dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["bearssl"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
