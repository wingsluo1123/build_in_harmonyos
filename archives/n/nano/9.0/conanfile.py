#!/usr/bin/env python3
"""Conan recipe for GNU nano 9.0."""

import os
import shutil

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NanoConan(ConanFile):
    name = "nano"
    version = "9.0"
    description = "Small and friendly command-line text editor"
    license = "GPL-3.0-or-later"
    homepage = "https://www.nano-editor.org/"
    url = "https://git.savannah.gnu.org/cgit/nano.git"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            ["--disable-nls", "--disable-libmagic", "--disable-speller"]
        )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        self._prepare_autotools_scripts()
        bash_path = shutil.which("bash")
        if bash_path:
            os.environ["CONFIG_SHELL"] = bash_path
            os.environ["SHELL"] = bash_path
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

    def _prepare_autotools_scripts(self):
        configure_path = os.path.join(self.source_folder, "configure")
        with open(configure_path, encoding="utf-8") as configure_file:
            configure_content = configure_file.read()
        umask_077_count = configure_content.count("umask 077")
        umask_022_count = configure_content.count("umask 022")
        if umask_077_count == 2:
            replace_in_file(self, configure_path, "umask 077", "umask 022")
        elif umask_077_count != 0 or umask_022_count < 2:
            raise RuntimeError("unexpected Autoconf temporary-directory guards")

        guess_path = os.path.join(self.source_folder, "config.guess")
        guess_anchor = (
            "case $UNAME_MACHINE:$UNAME_SYSTEM:"
            "$UNAME_RELEASE:$UNAME_VERSION in\n"
        )
        harmony_case = (
            guess_anchor
            + "    arm64:HarmonyOS:*:*)\n"
            + "\techo aarch64-unknown-linux-ohos\n"
            + "\texit ;;\n"
            + "    *:HarmonyOS:*:*)\n"
            + "\techo $UNAME_MACHINE-unknown-linux-ohos\n"
            + "\texit ;;\n"
        )
        with open(guess_path, encoding="utf-8") as guess_file:
            guess_content = guess_file.read()
        if "arm64:HarmonyOS:*:*)" not in guess_content:
            if guess_content.count(guess_anchor) != 1:
                raise RuntimeError("unexpected config.guess platform dispatch")
            replace_in_file(self, guess_path, guess_anchor, harmony_case)

        with open(guess_path, encoding="utf-8") as guess_file:
            if "arm64:HarmonyOS:*:*)" not in guess_file.read():
                raise RuntimeError("HarmonyOS config.guess case was not installed")
