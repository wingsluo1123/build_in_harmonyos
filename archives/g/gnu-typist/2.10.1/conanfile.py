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
        # Cross-compilation: only add --build/--host for OHOS builds
        if self.settings.os == "OHOS":
            tc.configure_args.append("--build=aarch64-linux-gnu")
            tc.configure_args.append("--host=aarch64-linux-gnu")
        # Suppress int-conversion error from bundled getopt.c (uses 0 as NULL)
        tc.extra_cflags.append("-Wno-int-conversion")
        # Define gettext stubs for NLS-disabled builds (via -include to avoid
        # shell quoting issues with parentheses in -D flags)
        tc.extra_cflags.append("-include")
        tc.extra_cflags.append("_tools/gettext_stub.h")
        tc.configure_args.append("--disable-nls")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        import os as _os
        # Save full environment to restore after build (R33)
        _saved_environ = dict(_os.environ)
        try:
            apply_conandata_patches(self)
            # [R33] PATH adjustments for OHOS platform limitations (E106/E079):
            #   - Prefix /bin: HMDFS GNU cat stdout permission issue (E106)
            #   - _tools/: help2man/makeinfo not available on OHOS (E079)
            _os.environ["PATH"] = "/bin:" + _saved_environ.get("PATH", "")
            # Create wrapper scripts for missing tools
            _os.makedirs("_tools", exist_ok=True)
            with open("_tools/help2man", "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            _os.chmod("_tools/help2man", 0o755)
            with open("_tools/makeinfo", "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            _os.chmod("_tools/makeinfo", 0o755)
            with open("_tools/gettext_stub.h", "w") as f:
                f.write("/* gettext stub for NLS-disabled builds */\n")
                f.write("#define gettext(x) (x)\n")
                f.write("#define _(x) (x)\n")
            _os.environ["PATH"] = _os.path.abspath("_tools") + ":" + _os.environ.get("PATH", "")
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
        finally:
            # R33: restore original environment after build
            _os.environ.clear()
            _os.environ.update(_saved_environ)

    def package(self):
        import os as _os
        _saved_path = _os.environ.get("PATH", "")
        try:
            # _tools/ created in build() — still on disk; add to PATH for install
            _tools_dir = _os.path.join(self.build_folder, "_tools")
            if _os.path.isdir(_tools_dir):
                _os.environ["PATH"] = _tools_dir + ":" + _saved_path
            autotools = Autotools(self)
            autotools.install()
        finally:
            _os.environ["PATH"] = _saved_path

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
