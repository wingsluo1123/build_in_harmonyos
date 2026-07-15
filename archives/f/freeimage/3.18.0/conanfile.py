#!/usr/bin/env python3
"""Conan recipe for FreeImage 3.18.0 on HarmonyOS.

FreeImage is a self-contained library that embeds all its dependencies
(libJPEG, libPNG, libTIFF, zlib, OpenJPEG, OpenEXR, LibRaw, LibWebP, LibJXR).
No external Conan dependencies are required.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class FreeimageConan(ConanFile):
    name = "freeimage"
    version = "3.18.0"
    description = "Open Source library project for supporting popular graphics image formats (PNG, BMP, JPEG, TIFF, WebP, etc.)"
    license = "FIPL/PL/GPL"
    homepage = "https://freeimage.sourceforge.io"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan profile conf, never from shell env vars.
        # OHOS Conan uses tools.build:compiler_executables as a dict, not sub-keys.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")

        # FreeImage uses a custom Makefile (Makefile.gnu), not autotools.
        # The Makefile already defines CFLAGS/CXXFLAGS with the correct flags
        # (including -DPNG_ARM_NEON_OPT=0 for aarch64 compatibility).
        # We pass CC and CXX from Conan to ensure the correct toolchain is used.
        # R9: Always use -j1
        self.run(f"make -C {self.source_folder} -f Makefile.gnu CC={cc} CXX={cxx} -j1")

    def package(self):
        # Install using the Makefile's install target with DESTDIR staging
        self.run(f"make -C {self.source_folder} -f Makefile.gnu install DESTDIR={self.package_folder} PREFIX=")

        # Fallback: also copy built artifacts directly
        copy(self, "FreeImage.h", src=os.path.join(self.source_folder, "Source"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libfreeimage.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            copy(self, "libfreeimage-3.18.0.so", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "lib"))
            copy(self, "libfreeimage.so*", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["freeimage"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["c++"]
