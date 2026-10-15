#!/usr/bin/env python3
"""Conan recipe for dte 1.9.1 — small console text editor (upstream GNU Make build)."""

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
import os


class DteConan(ConanFile):
    name = "dte"
    version = "1.9.1"
    description = (
        "Small and easy to use console text editor with multiple buffers/tabs, "
        "regex search and replace, syntax highlighting and a termios raw-mode "
        "editing loop (single self-contained binary)."
    )
    license = "GPL-2.0-or-later"
    homepage = "https://craigbarnes.gitlab.io/dte/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Zero external dependencies: terminfo is compiled out through the
        # upstream TERMINFO_DISABLE knob (OHOS ships no terminfo database, and
        # without it dte falls back to its built-in xterm/ecma48 driver), while
        # iconv is provided by libc on this platform.
        pass

    def layout(self):
        basic_layout(self)
        # Raw Makefile project: build in place, no separate build tree.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Official R33/R9 wiring: expose tools.build:compiler_executables
        # through the aggregated build environment scripts.
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: never take the compiler from shell $CC (unset on CI workers).
        # R9: build serially with -j1.
        # NOTE: tools.build:compiler_executables is registered as a dict conf,
        # so it must be read as a dict and then indexed (sub-field access with
        # "…:c" is rejected by conan with "does not exist in configuration list").
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = (executables or {}).get("c", "clang")
        self.run(f"make -j1 CC={cc} TERMINFO_DISABLE=1")
        # Upstream test suite (build/test/test) must really run in build()
        # (checklist #12 / rule4): `make check` builds and executes it.
        self.run(f"make check -j1 CC={cc} TERMINFO_DISABLE=1")

    def package(self):
        # Upstream `make install` shells out to install(1), which is not
        # on PATH on this platform (/bin is excluded from PATH), so copy
        # the exact same layout the install target produces:
        #   bin/dte, share/man/man1/dte.1,
        #   share/man/man5/{dterc.5,dte-syntax.5}
        copy(self, "dte", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, os.path.join("docs", "dte.1"), self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"))
        for man in ("dterc.5", "dte-syntax.5"):
            copy(self, os.path.join("docs", man), self.source_folder,
                 os.path.join(self.package_folder, "share", "man", "man5"))
        os.chmod(os.path.join(self.package_folder, "bin", "dte"), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
