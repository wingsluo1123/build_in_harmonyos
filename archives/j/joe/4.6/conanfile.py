#!/usr/bin/env python3
"""Conan recipe — joe 4.6 (Autotools)

Joe's Own Editor — full featured terminal-based screen editor.
Build system: autotools (configure + make).
License: GPL-1.0-or-later
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class JoeConan(ConanFile):
    name = "joe"
    version = "4.6"
    description = "Full featured terminal-based screen editor (Joe's Own Editor)"
    license = "GPL-1.0-or-later"
    homepage = "https://joe-editor.sourceforge.net/"
    url = "https://joe-editor.sourceforge.net/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ncurses is available as system prebuilt at ~/usr/local (not a Conan package)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # System prebuilt ncurses via DEFAULT_PREFIX (like bitwise/0.50)
        sysroot = os.environ.get("DEFAULT_PREFIX", os.path.expanduser("~/usr/local"))
        tc.extra_cflags.append(f"-I{sysroot}/include")
        # VPATH build: add source dirs to include path for types.h etc.
        src = self.source_folder
        tc.extra_cflags.append(f"-I{src}/joe")
        tc.extra_cflags.append(f"-I{src}/joe/util")
        tc.extra_ldflags.append(f"-L{sysroot}/lib")
        # R26: Terminal tools statically linked
        tc.extra_ldflags.append("-static")
        # Clang 15 strictness: older C code needs relaxed warnings
        tc.extra_cflags.append("-Wno-error=int-conversion")
        tc.extra_cflags.append("-Wno-error=implicit-function-declaration")
        tc.extra_cflags.append("-Wno-int-conversion")
        tc.extra_cflags.append("-Wno-implicit-function-declaration")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix CONFIG_SHELL from profile that may point to non-existent path
        bash_path = shutil.which("bash") or "/bin/sh"
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            # Remove binary-sign-tool calls from patch 0003
            # (conftest can execute directly on OHOS, sign-tool is not needed)
            content = content.replace(
                '  binary-sign-tool "./conftest$ac_exeext" 2>/dev/null || true\n', ''
            )
            content = content.replace(
                '  binary-sign-tool "./conftest$ac_cv_exeext" 2>/dev/null || true\n', ''
            )
            # Fix CONFIG_SHELL/SHELL paths (strace pattern)
            if content.startswith("#!"):
                shebang = content.split("\n", 1)[0]
                rest = content.split("\n", 1)[1] if "\n" in content else ""
                fallback = (
                    f'{shebang}\n'
                    f'# Override invalid paths from Conan profile\n'
                    f'if [ ! -x "$CONFIG_SHELL" ] 2>/dev/null; then\n'
                    f'  CONFIG_SHELL={bash_path}\n'
                    f'  export CONFIG_SHELL\n'
                    f'fi\n'
                    f'if [ ! -x "$SHELL" ] 2>/dev/null; then\n'
                    f'  SHELL={bash_path}\n'
                    f'  export SHELL\n'
                    f'fi\n'
                )
                content = fallback + rest
                with open(configure_path, "w") as f:
                    f.write(content)
        os.environ["CONFIG_SHELL"] = bash_path
        os.environ["SHELL"] = bash_path
        # E011: Fix umask 077 on HMDFS (setgid causes mktemp dir unwritable)
        for fn in ["configure", "config.status"]:
            p = os.path.join(self.source_folder, fn)
            if os.path.exists(p):
                with open(p, "r") as f:
                    content = f.read()
                content = content.replace("umask 077", "umask 022")
                with open(p, "w") as f:
                    f.write(content)
        autotools = Autotools(self)
        # R15: Force cross-compile mode to skip conftest execution on OHOS
        # OHOS security prevents running unsigned conftest binaries
        if self.settings.os == "OHOS":
            autotools.configure(args=["--build=x86_64-pc-linux-gnu",
                                       "--host=aarch64-unknown-linux-ohos"])
        else:
            autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # joe is a standalone binary tool, no libraries to export
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
