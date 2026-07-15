#!/usr/bin/env python3
"""Conan recipe — aamath 0.3 (Makefile).

aamath renders mathematical expressions as ASCII art text.
Build system: plain Makefile (no configure script).
Depends on readline + ncurses (pre-built system libraries).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AamathConan(ConanFile):
    name = "aamath"
    version = "0.3"
    description = "Render mathematical expressions as ASCII art text"
    license = "GPL-2.0-or-later"
    homepage = "https://cdn.netbsd.org/pub/pkgsrc/distfiles/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"aamath supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _find_sysroot(self):
        """Find prefix containing readline headers and libs."""
        candidates = [
            os.environ.get("DEFAULT_PREFIX"),
            os.path.expanduser("~/usr/local"),
            "/data/service/hnp",
            "/usr/local",
            "/usr",
        ]
        for path in candidates:
            if not path:
                continue
            if os.path.isfile(os.path.join(path, "include", "readline", "readline.h")):
                return path
        return None

    def _ensure_deps(self):
        """Ensure readline/ncurses are available, install from cmd-pkgs if missing."""
        sysroot = self._find_sysroot()
        if sysroot:
            return sysroot

        # Install readline + ncurses from cmd-pkgs
        self.run(
            "curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/"
            "releases/download/pkgs/install.sh | sh -s -- readline 8.2 ncurses 6.5",
            env="conanbuild",
        )
        sysroot = self._find_sysroot()
        if not sysroot:
            raise ConanInvalidConfiguration(
                "readline/ncurses not found and install failed. "
                "Install: curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/"
                "cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- readline 8.2 ncurses 6.5"
            )
        return sysroot

    def build(self):
        apply_conandata_patches(self)

        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cxx = comp.get("cpp", "clang++") if comp else "clang++"

        sysroot = self._ensure_deps()
        src = self.source_folder

        self.run(
            f"make -f Makefile.good -j1 "
            f"CXX='{cxx}' "
            f"LD='{cxx}' "
            f"CXXFLAGS='-Wall -O2 -fPIC -DUSE_READLINE -I{sysroot}/include' "
            f"LFLAGS='-L{sysroot}/lib' "
            f"LIBS='-lreadline -lncurses'",
            env="conanbuild",
            cwd=src,
        )

    def package(self):
        src = self.source_folder
        self.run(
            f"make -f Makefile.good install "
            f"PREFIX=/ DESTDIR={self.package_folder}",
            env="conanbuild",
            cwd=src,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["readline", "ncurses"]
