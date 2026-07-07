#!/usr/bin/env python3
"""Conan recipe — bash-completion 2.17.0 (autotools, needs autoreconf).

GitHub source archive does not include pre-generated configure script.
We run autoreconf -fi to generate it from configure.ac.
Uses config.status patching to work around autoconf 2.72 temp dir perms issue.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BashcompletionConan(ConanFile):
    name = "bash-completion"
    version = "2.17.0"
    description = "Programmable completion functions for bash"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/scop/bash-completion"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        tmpdir = "/storage/Users/currentUser/tmp"
        os.makedirs(tmpdir, exist_ok=True)

        env_prefix = (
            f'PATH="/storage/Users/currentUser/usr/local/bin:/data/service/hnp/bin:$PATH" '
            f'CONFIG_SHELL=/data/service/hnp/bin/bash '
            f'SHELL=/data/service/hnp/bin/bash '
            f'TMPDIR={tmpdir} '
            f'AWK=/data/service/hnp/bin/awk '
            f'umask 022 '
        )

        # Step 1: autoreconf to generate configure
        self.run(f'cd "{self.source_folder}" && {env_prefix} autoreconf -fi')

        # Step 2: configure
        self.run(f'cd "{self.source_folder}" && {env_prefix} ./configure --prefix= --no-create')

        # Step 3: Patch config.status to fix temp dir permissions
        cs = os.path.join(self.source_folder, "config.status")
        if os.path.exists(cs):
            with open(cs, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 000")
            content = content.replace(
                "ac_tmp=$tmp",
                'ac_tmp=$tmp\n  chmod 777 "$ac_tmp" 2>/dev/null'
            )
            with open(cs, "w") as f:
                f.write(content)

        # Step 4: config.status
        self.run(f'cd "{self.source_folder}" && {env_prefix} ./config.status')

        # Step 5: make
        self.run(f'cd "{self.source_folder}" && {env_prefix} make -j1')

    def package(self):
        env_prefix = (
            f'PATH="/storage/Users/currentUser/usr/local/bin:/data/service/hnp/bin:$PATH" '
            f'TMPDIR=/storage/Users/currentUser/tmp '
            f'AWK=/data/service/hnp/bin/awk '
        )
        self.run(f'cd "{self.source_folder}" && {env_prefix} make install DESTDIR="{self.package_folder}"')

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
