#!/usr/bin/env python3
"""Conan recipe — readline 8.3 (Autotools)"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class ReadlineConan(ConanFile):
    name = "readline"
    version = "8.3"
    description = "GNU Readline — library for command-line editing and history"
    license = "GPL-3.0-only"
    homepage = "https://tiswww.cwru.edu/php/chet/readline/rltop.html"

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

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: system-named library — default static to avoid polluting /lib /lib64
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        # Link against ncurses (system library on OHOS)
        tc.configure_args.append("--with-curses")
        # Force ncursesw (wide-char) — OHOS uses libncursesw, not libncurses
        tc.configure_args.append("bash_cv_termcap_lib=libncursesw")
        # Static lib needs -fPIC to be linkable into shared libraries downstream
        tc.extra_cflags.append("-fPIC")
        tc.extra_cflags.append("-O2")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS can't create ./confXXXXXX temp dirs (E002).
        # Redirect config.status tmpdir to $HOME/tmp.
        cfg = os.path.join(self.source_folder, "configure")
        home = os.environ.get("HOME", "/storage/Users/currentUser")
        self.run(f"sed -i 's|\"\\./conf|\"{home}/tmp/conf|g' {cfg}")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["readline", "history"]
