#!/usr/bin/env python3
"""Conan recipe for cdecl 18.7.2 — C/C++ declaration translator CLI."""
import os
import shutil

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CdeclConan(ConanFile):
    name = "cdecl"
    version = "18.7.2"
    description = "C/C++ declaration and cast translator command-line tool"
    license = "GPL-3.0-or-later"
    package_type = "application"
    homepage = "https://github.com/paul-j-lucas/cdecl"
    url = "https://github.com/paul-j-lucas/cdecl"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R5: OHOS has no /bin/sh; use bash when available.
        if self.settings.os in ("Linux", "OHOS"):
            bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
            tc.configure_args.append(f"SHELL={bash}")
        host_triplet = {"OHOS": "aarch64-unknown-linux-ohos"}.get(str(self.settings.os))
        if host_triplet:
            tc.configure_args.extend([
                f"--build={host_triplet}",
                f"--host={host_triplet}",
            ])
        # Avoid optional terminal libraries that are not required for batch CLI use.
        tc.configure_args.extend([
            "--without-readline",
            "--disable-term-size",
            "--disable-dependency-tracking",
            "--prefix=/",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # Release tarball ships src/config.h; out-of-source builds must use
        # the generated build config.h instead of the stale source copy.
        stale_config = os.path.join(self.source_folder, "src", "config.h")
        if os.path.exists(stale_config):
            os.remove(stale_config)
        autotools.make(args=["-j1"])

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "cdecl", src=os.path.join(self.build_folder, "src"), dst=bindir)
        cdecl_exe = os.path.join(bindir, "cdecl")
        for alias in ("c++decl", "explain"):
            alias_path = os.path.join(bindir, alias)
            if os.path.exists(alias_path):
                os.remove(alias_path)
            os.symlink(cdecl_exe, alias_path)
        copy(self, "*.1", src=os.path.join(self.source_folder, "share", "man", "man1"), dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
