#!/usr/bin/env python3
"""Conan recipe for gnu-typist 2.10.1 — Autotools project with system ncurses."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class GnutypistConan(ConanFile):
    name = "gnu-typist"
    version = "2.10.1"
    description = "GNU Typist — a typing tutor"
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/gtypist/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-linux-gnu")
        tc.configure_args.append("--host=aarch64-linux-gnu")
        tc.configure_args.append("--disable-nls")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        import os as _os
        # Fix HMDFS /tmp issue: replace mktemp -d with flat file approach
        # in the configure script's config.status generation
        _os.environ["PATH"] = "/bin:" + _os.environ.get("PATH", "")
        _os.environ["CC"] = "clang"
        _os.environ["CXX"] = "clang++"
        _os.environ["MAKEINFO"] = ":"
        # Create wrapper scripts for missing tools
        _os.makedirs("_tools", exist_ok=True)
        with open("_tools/help2man", "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        _os.chmod("_tools/help2man", 0o755)
        _os.environ["PATH"] = _os.path.abspath("_tools") + ":" + _os.environ.get("PATH", "")
        # Patch configure script to fix HMDFS mktemp issue (E106)
        # HMDFS doesn't allow creating files inside mktemp -d subdirs
        # configure is in the source folder, not the build folder
        configure_path = _os.path.join(self.source_folder, "configure")
        with open(configure_path, "r") as f:
            content = f.read()
        content = content.replace(
            'mktemp -d "./confXXXXXX"',
            'mktemp -p . confXXXXXX.tmp'
        )
        content = content.replace(
            'test -d "$tmp"',
            'test -d "$tmp2"'
        )
        # Fix the missing reference: tmp2 is set from the mktemp result
        # The mktemp -p creates a flat file, so we need to rm it and mkdir -p
        content = content.replace(
            'mktemp -p . confXXXXXX.tmp',
            'mktemp -p . confXXXXXX.tmp && tmp2="$tmp" && rm -f "$tmp" && mkdir -p "$tmp2"'
        )
        with open(configure_path, "w") as f:
            f.write(content)
        # Patch config.h to define gettext() stub (NLS disabled)
        config_h_path = _os.path.join(self.source_folder, "config.h.in")
        if _os.path.exists(config_h_path):
            with open(config_h_path, "a") as f:
                f.write('\n/* gettext stub for NLS-disabled builds */\n')
                f.write('#define gettext(x) (x)\n')
                f.write('#define _(x) (x)\n')
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
