#!/usr/bin/env python3
"""Conan recipe — ncurses 6.4 (Autotools)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NcursesConan(ConanFile):
    name = "ncurses"
    version = "6.4"
    description = "Terminal control library for Unix-like systems"
    license = "X11"
    homepage = "https://invisible-island.net/ncurses/"
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

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: system-name library — MUST be static by default to avoid polluting /lib
        # ncurses shared lib would hijack system libncursesw.so.6 causing zsh crash
        if not self.options.shared:
            tc.configure_args.append("--without-shared")
            tc.configure_args.append("--enable-static")
        tc.configure_args.append("--without-debug")
        tc.configure_args.append("--without-ada")
        tc.configure_args.append("--without-manpages")
        tc.configure_args.append("--without-tests")
        tc.configure_args.append("--without-cxx-binding")
        tc.configure_args.append("--enable-widec")
        tc.configure_args.append("--enable-overwrite")
        tc.extra_cflags.append("-fPIC")
        tc.extra_cflags.append("-O2")
        tc.generate()

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
        self.cpp_info.libs = ["ncursesw", "panelw", "menuw", "formw"]
