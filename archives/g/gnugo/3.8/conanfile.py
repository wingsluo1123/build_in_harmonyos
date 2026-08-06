#!/usr/bin/env python3
"""Conan recipe — GNU Go (gnugo) 3.8

GNU Go is a Go (board game) engine. It supports 9x9, 13x13, 19x19 boards,
multiple modes (ASCII, GMP, GTP), and SGF file support.

Build system: autotools (configure + make)
License: GPL-3.0-or-later
Homepage: https://www.gnu.org/software/gnugo/
"""
import stat
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class GnugoConan(ConanFile):
    name = "gnugo"
    version = "3.8"
    description = "GNU Go — Go (board game) engine"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gnugo/"
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
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS: mktemp -d creates dirs with broken group perms (HMDFS MAC),
        # causing config.status to fail writing temp files. Create a mktemp wrapper
        # that returns failure to force autoconf AS_TMPDIR to use mkdir fallback.
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            '#!/bin/sh\n'
            '# HarmonyOS: mktemp -d creates dirs with broken perms (HMDFS MAC).\n'
            '# Return failure to force autoconf AS_TMPDIR to use mkdir fallback.\n'
            'exit 1\n'
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        tc = AutotoolsToolchain(self)
        # HarmonyOS: config.guess doesn't recognize the OS, force build triplet
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

        # Prepend wrapper to PATH
        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        env.vars(self).save_script("hmos_env")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # L1: Run upstream official test suite (make check)
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
