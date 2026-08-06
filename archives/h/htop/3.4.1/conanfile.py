#!/usr/bin/env python3
"""Conan recipe for htop 3.4.1 — Interactive process viewer.

Autotools project (configure + make + make install).
System prebuilt ncurses via DEFAULT_PREFIX env var.
htop is a command-line application (not a library).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class HtopConan(ConanFile):
    name = "htop"
    version = "3.4.1"
    description = "Interactive process viewer for Unix systems"
    license = "GPL-2.0"
    homepage = "https://htop.dev/"
    url = "https://github.com/htop-dev/htop"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: Use `in ("Linux", "OHOS")` for settings.os check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"htop supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R33: Compiler/flags from Conan Toolchain, not shell env vars.
        # ncurses is a system prebuilt package (cmd-pkgs), installed to DEFAULT_PREFIX.
        # On OHOS CI workers, DEFAULT_PREFIX is set by the build environment.
        # Fallback to ~/usr/local for local development.
        sysroot = os.environ.get("DEFAULT_PREFIX") or os.path.expanduser("~/usr/local")
        sys_inc = os.path.join(sysroot, "include")
        sys_lib = os.path.join(sysroot, "lib")

        tc.extra_cflags.append(f"-I{sys_inc}")
        tc.extra_cflags.append(f"-I{os.path.join(sys_inc, 'ncursesw')}")
        tc.extra_cflags.append("-DNCURSES_WIDECHAR")
        tc.extra_ldflags.append(f"-L{sys_lib}")
        # R26: ncurses is a system-name library, must be statically linked
        # to avoid polluting /lib and SELinux runtime issues on OHOS
        tc.extra_ldflags.append("-static")

        # Fix: AutotoolsToolchain defaults to --prefix=package_folder,
        # and autotools.install() sets DESTDIR=package_folder.
        # Setting --prefix=/ makes install path: DESTDIR/bin/htop
        tc.configure_args.append("--prefix=/")
        tc.generate()

        # Set TMPDIR for config.status (OHOS /tmp is read-only, E002)
        env = Environment()
        tmpdir = os.path.expanduser("~/tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        env.vars(self).save_script("env_tmpdir")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # Use -j1 to avoid HMDFS FIFO issues with make jobserver
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
