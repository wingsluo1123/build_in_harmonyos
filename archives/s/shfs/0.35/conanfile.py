#!/usr/bin/env python3
"""Conan recipe — shfs 0.35

SSH filesystem mount tool (SourceForge project by Miroslav Spousta).
Userspace part only: shfsmount / shfsumount.

Build system: plain Makefile in shfsmount/, no configure step.
License: GPL-2.0-or-later (see Changelog / debian/copyright upstream)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class ShfsConan(ConanFile):
    name = "shfs"
    version = "0.35"
    description = "SSH-backed filesystem mount tool — mounts a remote shell/perl file tree locally (userspace utils only)"
    license = "GPL-2.0-or-later"
    homepage = "https://shfs.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        # debian/ ships changelog as a symlink to ../Changelog; conan's source→build
        # copy raises Errno 13 on it here, and the dir is distro packaging metadata
        # that never participates in the build.
        get(self, **self.conan_data["sources"], strip_root=True,
            excludes=["*/debian/*"])

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf, never a bare shell env var
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        # Fall back to the profile's declared compiler rather than a literal toolchain name.
        cc = comp_execs.get("c") or str(self.settings.compiler)
        # Only the `utils` subtree is built: `all` also descends into shfs/, which is a
        # Linux kernel module and has no counterpart on OHOS.
        # Command-line CC/LINKER override the Makefile's hard-coded `gcc` (make CLI wins
        # over both `:=` and `=` assignments); SHFS_VERSION stamps the version string.
        # -j1: single-directory 1990s Makefile, keeps interleaved output deterministic.
        self.run(
            f'make -j1 -C shfsmount CC="{cc}" LINKER="{cc}" '
            f'SHFS_VERSION="{self.version}"',
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        src = os.path.join(self.source_folder, "shfsmount")
        for tool in ("shfsmount", "shfsumount"):
            copy(self, tool, src=src, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # The two capability probes are the only test artifacts upstream ships.
        # Shipping them lets test_package execute the upstream cases verbatim,
        # instead of a re-typed copy.
        copy(self, "shell-test.in", src=src,
             dst=os.path.join(self.package_folder, "res", "shfs"))
        copy(self, "perl-test.in", src=src,
             dst=os.path.join(self.package_folder, "res", "shfs"))

    def package_info(self):
        # Command-line tools, not a library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]
