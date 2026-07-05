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
        hnp_bin = "/data/service/hnp/bin"
        current_path = os.environ.get("PATH", "")
        if hnp_bin not in current_path:
            os.environ["PATH"] = hnp_bin + ":" + current_path
        autotools_bin = "/storage/Users/currentUser/usr/local/bin"
        if autotools_bin not in current_path:
            os.environ["PATH"] = autotools_bin + ":" + os.environ.get("PATH", "")

        # Step 1: Run autoreconf to generate configure script
        self.run(
            f'cd "{self.source_folder}" && '
            f'CONFIG_SHELL=/data/service/hnp/bin/bash '
            f'SHELL=/data/service/hnp/bin/bash '
            f'TMPDIR={tmpdir} '
            f'AWK=/data/service/hnp/bin/awk '
            f'autoreconf -fi',
            env="conanrun"
        )

        # Step 2: Run configure --no-create
        self.run(
            f'cd "{self.source_folder}" && '
            f'umask 022 && '
            f'TMPDIR={tmpdir} '
            f'CONFIG_SHELL=/data/service/hnp/bin/bash '
            f'SHELL=/data/service/hnp/bin/bash '
            f'AWK=/data/service/hnp/bin/awk '
            f'PATH="/data/service/hnp/bin:$PATH" '
            f'./configure --prefix= --no-create',
            env="conanrun"
        )

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

        # Step 4: Run config.status manually (now patched)
        self.run(
            f'cd "{self.source_folder}" && '
            f'TMPDIR={tmpdir} '
            f'AWK=/data/service/hnp/bin/awk '
            f'PATH="/data/service/hnp/bin:$PATH" '
            f'./config.status',
            env="conanrun"
        )

        # Step 5: Run make
        self.run(
            f'cd "{self.source_folder}" && '
            f'TMPDIR={tmpdir} '
            f'AWK=/data/service/hnp/bin/awk '
            f'PATH="/data/service/hnp/bin:$PATH" '
            f'make -j1',
            env="conanrun"
        )

    def package(self):
        self.run(
            f'cd "{self.source_folder}" && '
            f'PATH="/data/service/hnp/bin:$PATH" '
            f'make install DESTDIR="{self.package_folder}"',
            env="conanrun"
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
