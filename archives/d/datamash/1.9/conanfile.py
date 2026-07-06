#!/usr/bin/env python3
"""Conan recipe — datamash 1.9 (Autotools, no deps).

GNU Datamash: command-line statistical/textual operations on input data.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DatamashConan(ConanFile):
    name = "datamash"
    version = "1.9"
    description = "GNU Datamash is a command-line program which performs basic numerical, textual and statistical operations on input data files"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/datamash/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E007/E072: patch config.sub for OHOS using sed (perl not available in conan env)
        config_sub = os.path.join(self.source_folder, "build-aux", "config.sub")
        if os.path.exists(config_sub):
            with open(config_sub, "r") as f:
                content = f.read()
            if "ohos-linux" not in content:
                content = content.replace(
                    "android-linux)\n\t\tbasic_machine=$field1-unknown\n\t\tbasic_os=linux-android",
                    "android-linux)\n\t\tbasic_machine=$field1-unknown\n\t\tbasic_os=linux-android\n\tohos-linux)\n\t\tbasic_machine=$field1-unknown\n\t\tbasic_os=linux-ohos"
                )
            if "ohos*" not in content:
                content = content.replace(
                    "gnu* | android* | bsd*",
                    "ohos* | gnu* | android* | bsd*"
                )
            if "linux-ohos" not in content:
                content = content.replace(
                    "linux-musl* | linux-relibc*",
                    "linux-musl* | linux-ohos* | linux-relibc*"
                )
            with open(config_sub, "w") as f:
                f.write(content)
        # E011: fix umask 077 -> 022 for HMDFS compatibility
        configure = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure):
            with open(configure, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure, "w") as f:
                f.write(content)
        autotools = Autotools(self)
        autotools.configure()
        # Workaround: makeinfo not available, touch info/doc files after configure
        # so make thinks they are up-to-date and skips regeneration
        build_dir = self.build_folder
        for doc_file in ["doc/datamash.info", "doc/stamp-vti", "doc/version.texi"]:
            fp = os.path.join(build_dir, doc_file)
            if os.path.exists(os.path.dirname(fp)):
                with open(fp, "w") as f:
                    f.write("")
                # Set timestamp to future to prevent regeneration
                os.utime(fp, (1e11, 1e11))
        # Also touch in source folder if different from build folder
        src_dir = self.source_folder
        if src_dir != build_dir:
            for doc_file in ["doc/datamash.info", "doc/stamp-vti", "doc/version.texi"]:
                fp = os.path.join(src_dir, doc_file)
                if os.path.exists(os.path.dirname(fp)):
                    with open(fp, "w") as f:
                        f.write("")
                    os.utime(fp, (1e11, 1e11))
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
