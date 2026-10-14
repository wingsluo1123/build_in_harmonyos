#!/usr/bin/env python3
"""Conan recipe for vile 9.8za (VI Like Emacs terminal editor)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class VileConan(ConanFile):
    name = "vile"
    version = "9.8za"
    description = "vile, a vi-like text editor with Emacs-style multiple windows and buffers"
    license = "GPL-2.0-or-later"
    homepage = "https://invisible-island.net/vile/"
    url = "https://invisible-island.net/archives/vile/current/vile-9.8za.tgz"
    topics = ("editor", "vi", "emacs", "terminal", "cli")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"vile supports Linux/OHOS only, got os={self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.6")

    def build_requirements(self):
        self.tool_requires("flex/2.6.4")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

        for name in ("configure", "config.guess", "config.sub", "install-sh", "missing"):
            path = os.path.join(self.source_folder, name)
            if os.path.exists(path):
                os.chmod(path, 0o755)

    def _writable_tmpdir(self):
        for key in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            candidate = (os.environ.get(key) or "").strip()
            if candidate and os.path.isdir(candidate) and os.access(candidate, os.W_OK):
                return candidate
        fallback = os.path.join(self.build_folder, "tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def _patch_autotools_tempdirs(self):
        replacements = (
            ("case `$ac_config_guess` in", "case $host_os in"),
            ("(umask 077 && mktemp -d", "(umask 022 && mktemp -d"),
            ("(umask 077 && mkdir", "(umask 022 && mkdir"),
        )
        for root in (self.source_folder, self.build_folder):
            for name in ("configure", "config.guess"):
                path = os.path.join(root, name)
                if not os.path.isfile(path):
                    continue
                with open(path, encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
                patched = content
                for old, new in replacements:
                    patched = patched.replace(old, new)
                if patched == content:
                    continue
                with open(path, "w", encoding="utf-8", newline="") as handle:
                    handle.write(patched)
                os.utime(path, None)

    def _patch_filters_makefile_paths(self):
        path = os.path.join(self.build_folder, "filters", "makefile")
        replacements = {
            "VPATH": os.path.join(self.source_folder, "filters"),
            "top_srcdir": self.source_folder,
            "srcdir": os.path.join(self.source_folder, "filters"),
        }
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
        for index, line in enumerate(lines):
            for key, value in replacements.items():
                if line.startswith(key):
                    lines[index] = f"{key}\t\t= {value}"
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--prefix=/",
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
            "--with-screen=ncursesw",
            "--disable-rpath-hack",
        ])
        tc.generate()

    def build(self):
        tmpdir = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        self._patch_autotools_tempdirs()

        # CI make does not resolve the filters VPATH, so mirror its sources
        # into the Autotools build directory before configure runs.
        filters_build = os.path.join(self.build_folder, "filters")
        os.makedirs(filters_build, exist_ok=True)
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "filters"),
            dst=filters_build,
        )

        autotools = Autotools(self)
        autotools.configure()
        self._patch_filters_makefile_paths()
        autotools.make(args=["-j1"])
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
