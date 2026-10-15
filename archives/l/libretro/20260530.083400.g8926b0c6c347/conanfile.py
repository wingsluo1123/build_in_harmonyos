#!/usr/bin/env python3
"""Conan recipe — libretro 20260530.083400.g8926b0c6c347 (libretro core, plain Makefile).

Upstream is the libretro port of Yabause (Sega Saturn emulator), pinned to
master commit 8926b0c6c347f8c5c755911ddb0ac695420ffbf8 (2026-05-30). The
upstream build is a plain Makefile under yabause/src/libretro producing the
shared plugin yabause_libretro.so, which libretro frontends load by exact
filename via dlopen.

The core is fully self-contained: zlib 1.2.11, LZMA, FLAC 1.3.3, libchdr and
libretro-common are all vendored in-tree (yabause/src/libchdr/deps/ and
yabause/src/libretro/libretro-common/), so there are no registry
requirements — only the system pthreads (-pthread).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibretroConan(ConanFile):
    name = "libretro"
    version = "20260530.083400.g8926b0c6c347"
    description = "Yabause Sega Saturn emulator libretro core (libretro/yabause, OHOS port)"
    license = "GPL-2.0"
    homepage = "https://github.com/libretro/yabause"
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

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Plain Makefile (no configure). The libretro glue lives in
        # yabause/src/libretro and compiles the emulator core from
        # $(SOURCE_DIR) = yabause/src plus the vendored deps. CC/CXX resolve
        # from the OHOS profile buildenv PATH (/data/service/hnp/bin).
        # -j1 avoids jobserver issues on constrained CI workers (HMFS).
        # Output is redirected to a file (then echoed back): when conan's
        # stdout is a pipe, large compiler writes to the inherited pipe can
        # fail in constrained sandboxes and the toolchain dies with no
        # diagnostic; writing to a file first makes failures fast and logged.
        self.run("make CC=clang CXX=clang++ -j1 > make-build.log 2>&1; "
                 "rc=$?; cat make-build.log; exit $rc",
                 cwd=os.path.join(self.source_folder, "yabause", "src", "libretro"))

    def package(self):
        copy(self, "yabause_libretro.so",
             src=os.path.join(self.source_folder, "yabause", "src", "libretro"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libretro.h",
             src=os.path.join(self.source_folder, "yabause", "src", "libretro",
                              "libretro-common", "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "COPYING",
             src=os.path.join(self.source_folder, "yabause"),
             dst=self.package_folder)

    def package_info(self):
        # Libretro cores are dlopen'ed by exact filename by frontends; the
        # public consumer surface is libretro.h + the retro_* ABI exported
        # by the plugin. No linkable library, no executables.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
