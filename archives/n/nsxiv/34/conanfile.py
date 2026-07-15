#!/usr/bin/env python3
"""Conan recipe for nsxiv (Neo Simple X Image Viewer) — Makefile project.

nsxiv is a lightweight image viewer for X11, forked from sxiv.
Build system: plain Makefile with config.mk.

Dependencies (system packages, installed via cmd-pkgs to ~/usr/local):
  - imlib2 (built with X11 display support)
  - libX11
  - libexif (optional, enabled)
  - libXext (indirect, via imlib2)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class NsxivConan(ConanFile):
    name = "nsxiv"
    version = "34"
    description = "Neo Simple X Image Viewer — lightweight image viewer fork of sxiv"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/nsxiv/nsxiv"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # System packages installed to ~/usr/local via cmd-pkgs
        sys_prefix = os.path.expanduser("~/usr/local")
        # Create config.h from config.def.h
        self.run("cp config.def.h config.h")
        # Create .git/index for Makefile version.h rule
        self.run("mkdir -p .git && touch .git/index")
        self.run('printf \'#define VERSION "34"\\n\' > version.h')
        # Build nsxiv
        # HAVE_INOTIFY=0: OHOS kernel lacks inotify API
        # HAVE_LIBFONTS=0: libXft not available on OHOS
        # HAVE_LIBEXIF=1: libexif available
        self.run(
            f"make CC=clang "
            f'HAVE_INOTIFY=0 HAVE_LIBFONTS=0 HAVE_LIBEXIF=1 '
            f'CFLAGS="-Wall -pedantic -O2 -DNDEBUG -fPIC" '
            f'CPPFLAGS="-I{sys_prefix}/include -I{sys_prefix}/include/X11" '
            f'LDLIBS="-L{sys_prefix}/lib" -j1'
        )

    def package(self):
        # Install nsxiv to package folder
        prefix = self.package_folder
        self.run(
            f"make install PREFIX={prefix} "
            "HAVE_INOTIFY=0 HAVE_LIBFONTS=0 HAVE_LIBEXIF=1"
        )

    def package_info(self):
        # nsxiv is a binary-only package (no library)
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # System libraries nsxiv links against
        self.cpp_info.system_libs = ["Imlib2", "X11", "exif"]
