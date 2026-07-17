#!/usr/bin/env python3
"""Conan 2.x recipe — tmux 3.4

Terminal multiplexer. Autotools build with patches for HarmonyOS:
- HMDFS temp dir fix (configure uses $TMPDIR)
- forkpty compatibility (__OHOS__ guard)
- config.guess/config.sub platform recognition
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TmuxConan(ConanFile):
    name = "tmux"
    version = "3.4"
    description = "Terminal multiplexer"
    license = "ISC"
    homepage = "https://tmux.github.io/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.4@ohpcd/stable")
        self.requires("libevent/2.1.12@ohpcd/stable")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["tmux"]
