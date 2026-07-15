#!/usr/bin/env python3
"""Conan recipe for rhash 1.4.6 — hash computation tool and library.

Build system: Makefile + configure script.
Produces: librhash.a (static library), rhash (CLI binary).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RhashConan(ConanFile):
    name = "rhash"
    version = "1.4.6"
    description = "Recursive hash computation tool supporting multiple hash algorithms"
    license = "MIT"
    homepage = "http://rhash.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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

        src = self.source_folder

        # R5: Use CONFIG_SHELL for configure scripts (OHOS has no /bin/sh)
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        # Run configure with platform-specific options
        self.run(f"cd {src} && {config_shell} ./configure --prefix={self.package_folder} "
                 f"--enable-static --disable-lib-shared --disable-gettext")

        # R9: Always use -j1
        self.run(f"cd {src} && make -j1")

    def package(self):
        # Copy public headers
        copy(self, "rhash.h", os.path.join(self.source_folder, "librhash"),
             os.path.join(self.package_folder, "include", "librhash"))
        copy(self, "rhash_torrent.h", os.path.join(self.source_folder, "librhash"),
             os.path.join(self.package_folder, "include", "librhash"))

        # Copy static library
        copy(self, "librhash.a", os.path.join(self.source_folder, "librhash"),
             os.path.join(self.package_folder, "lib"))

        # Copy rhash binary
        copy(self, "rhash", self.source_folder,
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["rhash"]
        self.cpp_info.includedirs = ["include/librhash"]
        self.cpp_info.bindirs = ["bin"]
