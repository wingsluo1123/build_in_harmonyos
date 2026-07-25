#!/usr/bin/env python3
"""Conan recipe for gnu-typist 2.10.1 — Autotools project with system ncurses."""
from conan import ConanFile
from conan.tools.files import get
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
        pass

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
        tc.configure_args.append("--disable-nls")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        import os as _os
        # Fix HMDFS mktemp issue (E106): configure's config.status uses
        # mktemp -d which fails on HMDFS; use mktemp -p + rm + mkdir instead.
        _os.environ["PATH"] = "/bin:" + _os.environ.get("PATH", "")
        # Disable documentation generation via MAKEINFO (missing makeinfo on OHOS)
        _os.environ["MAKEINFO"] = ":"
        # Create wrapper scripts for missing tools
        _os.makedirs("_tools", exist_ok=True)
        with open("_tools/help2man", "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        _os.chmod("_tools/help2man", 0o755)
        _os.environ["PATH"] = _os.path.abspath("_tools") + ":" + _os.environ.get("PATH", "")
        # Patch configure's mktemp to work around HMDFS limitation (E106):
        # mktemp -d creates files not writable on HMDFS; replace with
        # mktemp -p + rm + mkdir approach using local variable 't'.
        configure_path = _os.path.join(self.source_folder, "configure")
        if _os.path.exists(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            old = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`'
            new = 'tmp=`(umask 077 && t=$(mktemp -p . confXXXXXX.tmp) && rm -f "$t" && mkdir -p "$t" && echo "$t") 2>/dev/null`'
            if old in content:
                content = content.replace(old, new)
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
