#!/usr/bin/env python3
"""Conan recipe for cproto — C function prototype generation tool."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CprotoConan(ConanFile):
    name = "cproto"
    version = "4.7y"
    description = "C function prototype generator — extracts function declarations from C source files"
    license = "GPL-2.0-or-later"
    homepage = "https://invisible-mirror.net/cproto/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

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
        tc.generate()

    def _fix_hmdfs_umask(self, filepath):
        """Fix HMDFS umask 077 permission issue in shell scripts.

        On HMDFS, (umask 077 && mktemp) creates directories that are not
        writable by the current process. Remove umask 077 and add chmod 777.
        """
        if not os.path.exists(filepath):
            return
        with open(filepath, "r") as f:
            content = f.read()
        # Remove umask 077 from mktemp calls and add chmod 777
        content = content.replace(
            '(umask 077 && mktemp -d',
            '(mktemp -d'
        )
        content = content.replace(
            '(umask 077 && mkdir "$tmp")',
            '(mkdir "$tmp" && chmod 777 "$tmp")'
        )
        # Also fix any standalone umask 077
        content = content.replace("umask 077", "umask 000")
        with open(filepath, "w") as f:
            f.write(content)

    def build(self):
        apply_conandata_patches(self)

        # E002/HMDFS: Fix umask 077 in configure before running it
        # so that generated config.status also avoids the issue
        if self.settings.os in ("OHOS", "Linux"):
            self._fix_hmdfs_umask(os.path.join(self.source_folder, "configure"))

        autotools = Autotools(self)
        autotools.configure()

        # E002: Disable HAVE_TMPFILE — system tmpfile() fails on HMDFS (/tmp read-only)
        config_h = os.path.join(self.source_folder, "config.h")
        if os.path.exists(config_h):
            with open(config_h, "r") as f:
                content = f.read()
            content = content.replace(
                "#define HAVE_TMPFILE 1",
                "/* #undef HAVE_TMPFILE */"
            )
            with open(config_h, "w") as f:
                f.write(content)

        # R6/generated-file fix: config.status uses umask 077 with mktemp,
        # which creates unwritable dirs on HMDFS. This is a generated file
        # (not source), so patching is not applicable.
        if self.settings.os in ("OHOS", "Linux"):
            config_status = os.path.join(self.source_folder, "config.status")
            self._fix_hmdfs_umask(config_status)
            if os.path.exists(config_status):
                self.run("sh ./config.status", cwd=self.source_folder)

        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
