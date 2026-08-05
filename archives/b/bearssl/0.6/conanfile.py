#!/usr/bin/env python3
"""Conan recipe for BearSSL 0.6 — custom Makefile build system.

BearSSL uses a custom Makefile with configuration files in conf/.
Build: make CONF=Ohos lib  (static library)
The conf/Ohos.mk is generated in generate() to configure clang for OHOS.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout


class BearsslConan(ConanFile):
    name = "bearssl"
    version = "0.6"
    description = "Optimized SSL/TLS library for embedded systems, pure C with no external dependencies"
    license = "MIT"
    homepage = "https://www.bearssl.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        pass

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Create conf/Ohos.mk for OHOS build with clang
        ohos_mk = os.path.join(self.source_folder, "conf", "Ohos.mk")
        os.makedirs(os.path.dirname(ohos_mk), exist_ok=True)
        with open(ohos_mk, "w") as f:
            f.write(
                'include conf/Unix.mk\n'
                'BUILD = ohos\n'
                'CC = clang\n'
                'LD = clang\n'
                'LDDLL = clang\n'
                'AR = llvm-ar\n'
            )

    def build(self):
        apply_conandata_patches(self)
        self.run("make CONF=Ohos lib", cwd=self.source_folder)

    def package(self):
        # Copy static library
        ohos_dir = os.path.join(self.source_folder, "ohos")
        copy(self, "libbearssl.a", ohos_dir, os.path.join(self.package_folder, "lib"))
        # Copy headers
        copy(self, "*.h",
             os.path.join(self.source_folder, "inc"),
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["bearssl"]
