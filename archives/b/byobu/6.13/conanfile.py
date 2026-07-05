#!/usr/bin/env python3
"""Conan recipe — byobu 6.13 (manual autotools build).

byobu is a shell-script based terminal multiplexer wrapper.
Uses autotools (configure.ac + Makefile.am) but needs:
1. autoreconf to generate configure script
2. Patch configure to replace umask 077 with umask 022
   (OHOS filesystem doesn't allow writing to dirs created with umask 077)
3. Run configure/make from source folder
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class ByobuConan(ConanFile):
    name = "byobu"
    version = "6.13"
    description = "byobu 6.13 - terminal multiplexer wrapper"
    license = "MIT"
    homepage = "https://github.com/dustinkirkland/byobu"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # tmux, screen, python-newt, gsed are runtime deps, not build deps

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        # Fix home ownership check for OHOS (was a patch, now inline)
        byobu_in = os.path.join(self.source_folder, 'usr', 'bin', 'byobu.in')
        if os.path.isfile(byobu_in):
            with open(byobu_in, 'r') as f:
                content = f.read()
            old_line = 'if [ ! -O "$HOME" ]; then'
            new_line = 'if [ ! -O "$HOME" ] && [ -z "$__OHOS__" ]; then'
            if old_line in content:
                content = content.replace(old_line, new_line, 1)
                with open(byobu_in, 'w') as f:
                    f.write(content)

        src = self.source_folder
        prefix = self.package_folder

        # Generate configure script from configure.ac
        self.run(f"cd {src} && autoreconf -fi", env="conanbuild")

        # Patch configure: replace umask 077 with umask 022
        # (OHOS filesystem doesn't allow writing to dirs created with umask 077)
        configure_path = os.path.join(src, "configure")
        with open(configure_path, 'r') as f:
            configure_content = f.read()
        configure_content = configure_content.replace("umask 077", "umask 022")
        with open(configure_path, 'w') as f:
            f.write(configure_content)

        # Run configure from source folder
        self.run(
            f'cd {src} && ./configure --prefix="{prefix}" '
            f'--bindir="{os.path.join(prefix, "bin")}" '
            f'--sysconfdir="{os.path.join(prefix, "etc")}"',
            env="conanbuild"
        )

        # Run make from source folder
        self.run(f"make -C {src} -j1", env="conanbuild")

    def package(self):
        src = self.source_folder
        self.run(f"make -C {src} install", env="conanbuild")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin", "share"]
