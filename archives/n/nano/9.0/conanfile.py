#!/usr/bin/env python3
"""Conan recipe for GNU nano 9.0."""

import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
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
        default_prefix = str(Path.home() / "usr" / "local")
        system_prefix = Path(
            self.conf.get(
                "user.nano:system_prefix",
                default=default_prefix,
                check_type=str,
            )
        )
        include_dir = system_prefix / "include"
        library_dir = system_prefix / "lib"
        missing = [
            str(path) for path in (include_dir, library_dir) if not path.is_dir()
        ]
        if missing:
            raise ConanInvalidConfiguration(
                "nano requires the system ncurses prefix; missing directories: "
                + ", ".join(missing)
                + ". Set user.nano:system_prefix in the Conan profile."
            )
        toolchain.extra_cflags.extend(
            [f"-I{include_dir}", f"-I{include_dir / 'ncursesw'}"]
        )
        toolchain.extra_ldflags.append(f"-L{library_dir}")
        toolchain.configure_args.extend(
            ["--disable-nls", "--disable-libmagic", "--disable-speller"]
        )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
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
