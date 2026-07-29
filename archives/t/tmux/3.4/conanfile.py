#!/usr/bin/env python3
"""Conan recipe for tmux 3.4."""

import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class TmuxConan(ConanFile):
    name = "tmux"
    version = "3.4"
    description = "Terminal multiplexer"
    license = "ISC"
    homepage = "https://github.com/tmux/tmux"
    url = "https://github.com/tmux/tmux"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libevent/2.1.12")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        default_prefix = str(Path.home() / "usr" / "local")
        system_prefix = Path(
            self.conf.get(
                "user.tmux:system_prefix",
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
                "tmux requires the system ncurses prefix; missing directories: "
                + ", ".join(missing)
                + ". Set user.tmux:system_prefix in the Conan profile."
            )
        tc.extra_cflags.append(f"-I{include_dir}")
        tc.extra_ldflags.append(f"-L{library_dir}")
        tc.configure_args.append("--enable-static")
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
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
