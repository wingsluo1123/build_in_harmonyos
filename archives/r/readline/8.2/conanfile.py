#!/usr/bin/env python3
"""Conan recipe — readline 8.2 (Autotools)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class ReadlineConan(ConanFile):
    name = "readline"
    version = "8.2"
    description = "GNU Readline library for command-line editing and history"
    license = "GPL-3.0-only"
    homepage = "https://tiswww.case.edu/php/chet/readline/rltop.html"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.4", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: system-name library — disable shared by default to avoid polluting /lib
        if not self.options.shared:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        # Use ncurses as terminal library
        tc.configure_args.append("--with-curses=yes")
        # Critical: -fPIC required for static lib to be linkable into shared libs on OHOS
        if self.options.fPIC:
            tc.extra_cflags.append("-fPIC")
        tc.extra_cflags.append("-O2")
        tc.generate()

        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # E167: Fix config.status temp directory on OHOS (HMDFS mktemp permission issue)
        if self.settings.os in ("Linux", "OHOS"):
            config_status = os.path.join(self.source_folder, "config.status")
            fixed_tmp = os.path.join(self.build_folder, "fixed_tmp")
            os.makedirs(fixed_tmp, exist_ok=True)
            replace_in_file(self, config_status, "ac_tmp=$tmp", f"ac_tmp={fixed_tmp}")
        autotools.make()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["history", "readline"]
