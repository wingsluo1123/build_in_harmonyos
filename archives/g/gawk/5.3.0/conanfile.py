#!/usr/bin/env python3
"""Conan recipe for gawk 5.3.0 — GNU Awk text processing language.

Build system: Autotools (configure + make).
gawk is a command-line tool (application), not a library.

OHOS adaptation:
  - config.guess/config.sub: HarmonyOS platform detection
  - fstat() EACCES handling for pipes/terminals/sockets
  - _BSD_SOURCE → _GNU_SOURCE in extensions
  - pma.h include path fix
  - config.status umask 077 fix for HMDFS (tmpfs blocks writes to
    directories created with umask 077 / no group access)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GawkConan(ConanFile):
    name = "gawk"
    version = "5.3.0"
    description = "GNU implementation of the AWK text processing language"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gawk/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: settings.os must be Linux or OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _fix_umask_in_configure(self, src_dir):
        """Fix HMDFS umask 077 issue in configure scripts.

        HarmonyOS tmpfs blocks writes to directories created with umask 077
        (no group access). The autoconf-generated configure script uses
        umask 077 for its config.status temp directory, causing
        'Permission denied' when creating Makefiles.
        This patches configure scripts to use umask 0 before running them.
        """
        for cfg_rel in ("configure", "extension/configure"):
            cfg_path = os.path.join(src_dir, cfg_rel)
            if os.path.isfile(cfg_path):
                with open(cfg_path, "r") as f:
                    content = f.read()
                if "umask 077" in content:
                    content = content.replace("umask 077", "umask 0")
                    with open(cfg_path, "w") as f:
                        f.write(content)

    def build(self):
        apply_conandata_patches(self)

        # Fix HMDFS umask 077 issue before running configure
        self._fix_umask_in_configure(self.source_folder)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = []
