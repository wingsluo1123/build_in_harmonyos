#!/usr/bin/env python3
"""Conan recipe for GNU Chess 6.3.0."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GnuChessConan(ConanFile):
    name = "gnu-chess"
    version = "6.3.0"
    description = "GNU command-line chess engine"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/chess/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    win_bash = True

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("gnu-chess supports POSIX platforms")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        basic_layout(self)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                "--without-readline",
                "--disable-nls",
                "ac_cv_func_malloc_0_nonnull=yes",
                "ac_cv_func_realloc_0_nonnull=yes",
            ]
        )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            config_sub = os.path.join(self.source_folder, "config.sub")
            replace_in_file(
                self,
                config_sub,
                "gnu* | android* | bsd*",
                "gnu* | android* | ohos* | bsd*",
            )
            replace_in_file(
                self,
                config_sub,
                "linux-gnu* | linux-dietlibc* | linux-android*",
                "linux-gnu* | linux-ohos* | linux-dietlibc* | linux-android*",
            )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        self.runenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
