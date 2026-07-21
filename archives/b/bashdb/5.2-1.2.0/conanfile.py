#!/usr/bin/env python3
"""Conan recipe — bashdb 5.2-1.2.0 (pure bash script debugger).

bashdb is a gdb-style debugger for bash scripts. It is a pure bash
script package (no compiled binaries); configure only checks the bash
version and make install copies scripts into place.

Adaptation notes:
  - configure only accepts bash 5.0/5.1/5.2; patch 0001 adds 5.3.
  - --with-bash points configure at the bash/5.3 dependency binary.
  - --build triplet forces config.guess to skip OHOS detection.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BashdbConan(ConanFile):
    name = "bashdb"
    version = "5.2-1.2.0"
    description = "Bash Debugger — gdb-style debugger for bash scripts"
    license = "GPL-2.0"
    homepage = "https://bashdb.sourceforge.net/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("bash/5.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Point configure at the bash/5.3 dependency binary so it can
        # detect version 5.3 (patch 0001 makes configure accept 5.3).
        bash_pkg = self.dependencies["bash"]
        bash_path = os.path.join(bash_pkg.package_folder, "bin", "bash")
        tc.configure_args.append(f"--with-bash={bash_path}")
        # config.guess does not know OHOS; force a linux triplet (R32).
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
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
        # bashdb installs bin/bashdb (script); no compiled libs.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
