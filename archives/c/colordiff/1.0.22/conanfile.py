#!/usr/bin/env python3
"""Conan recipe for colordiff 1.0.22 — pure Perl script project.

colordiff is a wrapper/replacement for 'diff' producing colourful output.
It is a pure Perl script with no compilation step; "installation" consists
of running 'make install' which copies the Perl script, man pages, and
config files to the appropriate directories.

Build system: Makefile (no configure script).
License: GPL-2.0-or-later

Platform adaptations for OHOS:
  1. Shebang fix: #!/usr/bin/perl -> #!/usr/bin/env perl (no /usr/bin/perl on OHOS)

R32: OHOS platform compatibility via os check.
R28: test_package/ exists.
R38: commands.json declared (command-line tool).
"""
import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ColordiffConan(ConanFile):
    name = "colordiff"
    version = "1.0.22"
    description = "A wrapper/replacement for 'diff' producing colourful output (pure Perl script)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.colordiff.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Stage install into a temporary directory within build folder
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)

        install_dir = os.path.join(staging, "bin")
        man_dir = os.path.join(staging, "share", "man", "man1")
        etc_dir = os.path.join(staging, "etc")

        self.run(
            f'make install '
            f'DESTDIR="" '
            f'INSTALL_DIR="{install_dir}" '
            f'MAN_DIR="{man_dir}" '
            f'ETC_DIR="{etc_dir}"',
            cwd=self.source_folder
        )

        # Ensure scripts are executable
        for fname in os.listdir(install_dir):
            fpath = os.path.join(install_dir, fname)
            if os.path.isfile(fpath):
                os.chmod(fpath, os.stat(fpath).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        # Copy staged files to package folder
        copy(self, "*", src=staging, dst=self.package_folder, keep_path=True)

    def package_info(self):
        # colordiff is a command-line tool, not a library
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
