#!/usr/bin/env python3
"""Conan recipe — spellcast 1.0

Spellcast: classic hand-waving multi-player X11 game of spellcasting.
Upstream: Andrew Plotkin (1993), based on Richard Bartle's Spellbinder.
Build system: simple Makefile (1994-era, no configure).
Produces: bin/spellcast (X11 executable) + man page + spelllist.ps.

OHOS adaptation:
  - Makefile hardcodes -I/usr/local/include -L/usr/local/lib;
    replaced with conan libx11 include/lib paths (R1: minimal flags).
  - LOGDIR="/tmp" kept as build-time define (runtime path; OHOS /tmp read-only
    is a runtime concern, not build blocker).
  - K&R C (1993) requires -std=gnu89 to compile with modern clang.
  - CC passed explicitly because bare `cc` is not in conanbuild PATH.
  - package_type: application (GUI game, not a library).

License: freely redistributable (non-commercial), retained copyright notice.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class SpellcastConan(ConanFile):
    name = "spellcast"
    version = "1.0"
    description = "Spellcast — a classic hand-waving multi-player X11 game of spellcasting"
    license = "LicenseRef-Custom"
    homepage = "https://www.eblong.com/zarf/spellcast.html"
    url = "http://archive.ubuntu.com/ubuntu/pool/multiverse/s/spellcast/spellcast_1.0.orig.tar.gz"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libx11/1.8.13.1")
        # libx11 doesn't propagate xorgproto headers (known behavior)
        self.requires("xorgproto/2025.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"]["1.0"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Explicit CC: the Makefile uses bare `cc` for implicit rules, and
        # conanbuild env may not propagate CC on OHOS profile (R33: do not
        # rely on undefined shell vars). Read the toolchain conf path.
        try:
            cc = self.conf_info["tools.build:compiler_executables"]["c"]
        except (KeyError, TypeError):
            cc = "/data/service/hnp/bin/clang"

        libx11_dep = self.dependencies["libx11"]
        xorgproto_dep = self.dependencies["xorgproto"]
        inc_dirs = [
            os.path.join(libx11_dep.package_folder, "include"),
            os.path.join(xorgproto_dep.package_folder, "include"),
        ]
        lib_dir = os.path.join(libx11_dep.package_folder, "lib").replace("\\", "/")
        inc_flags = " ".join(f"-I{d}" for d in inc_dirs)

        makefile = os.path.join(self.source_folder, "Makefile")
        with open(makefile, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Replace hardcoded /usr/local paths with conan include/lib paths
        content = content.replace("-I/usr/local/include", inc_flags)
        content = content.replace("-L/usr/local/lib", f"-L{lib_dir}")

        # K&R-era C (1993): add -std=gnu89 to allow implicit int returns,
        # implicit function declarations, and int-to-pointer casts used
        # throughout the codebase. Suppress specific warnings that become
        # errors in modern clang.
        content = content.replace(
            "CFLAGS = -g ",
            "CFLAGS = -g -std=gnu89 "
            "-Wno-deprecated-non-prototype -Wno-int-conversion "
            "-Wno-return-type -Wno-incompatible-pointer-types "
        )

        with open(makefile, "w", encoding="utf-8") as f:
            f.write(content)

        # Build the X11 version, pass CC explicitly for implicit rules
        self.run(f"make -j1 spellcast CC={cc}", cwd=self.source_folder, env="conanbuild")

    def package(self):
        src = self.source_folder
        dst = self.package_folder

        # Binary
        copy(self, "spellcast", src=src, dst=os.path.join(dst, "bin"), keep_path=False)

        # Man page
        copy(self, "spellcast.6", src=src, dst=os.path.join(dst, "share", "man", "man6"), keep_path=False)

        # Spell list (PostScript)
        copy(self, "spelllist.ps", src=src, dst=os.path.join(dst, "share", "spellcast"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
