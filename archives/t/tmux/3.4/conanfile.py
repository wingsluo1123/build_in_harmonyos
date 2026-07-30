#!/usr/bin/env python3
"""Conan recipe for tmux 3.4."""

import os
import shlex
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
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
        sources = self.conan_data["sources"]
        get(self, **sources["tmux"], strip_root=True)
        get(
            self,
            **sources["ncurses"],
            destination=self._ncurses_source_folder(),
            strip_root=True,
        )

    def _ncurses_source_folder(self):
        return os.path.join(self.source_folder, "_ncurses")

    def _ncurses_prefix(self):
        return os.path.join(self.build_folder, "ncurses-prefix")

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        ncurses_prefix = Path(self._ncurses_prefix())
        include_dir = ncurses_prefix / "include"
        library_dir = ncurses_prefix / "lib"
        tc.extra_cflags.append(f"-I{include_dir}")
        tc.extra_cflags.append(f"-I{include_dir / 'ncursesw'}")
        tc.extra_ldflags.append(f"-L{library_dir}")
        tc.configure_args.append("--enable-static")
        tc.extra_ldflags.append("-static")
        tc.generate()

    def _build_ncurses(self):
        build_folder = os.path.join(self.build_folder, "ncurses-build")
        os.makedirs(build_folder, exist_ok=True)

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compiler_executables.get("c")
        cxx = compiler_executables.get("cpp")
        if not cc or not cxx:
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables must define c and cpp"
            )

        configure_args = [
            os.path.join(self._ncurses_source_folder(), "configure"),
            f"--prefix={self._ncurses_prefix()}",
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--without-shared",
            "--with-normal",
            "--enable-widec",
            "--with-termlib",
            "--without-cxx",
            "--without-cxx-binding",
            "--without-progs",
            "--without-tests",
            "--without-manpages",
        ]
        build_env = Environment()
        build_env.define("CC", cc)
        build_env.define("CXX", cxx)
        build_env.define("CFLAGS", "-fPIC")
        build_env.define("CPPFLAGS", "-D_GNU_SOURCE")
        with build_env.vars(self).apply():
            self.run(shlex.join(configure_args), cwd=build_folder)
            self.run("make -j1", cwd=build_folder)
            self.run("make install.libs install.includes", cwd=build_folder)

    def build(self):
        apply_conandata_patches(self)
        self._build_ncurses()

        ncurses_prefix = Path(self._ncurses_prefix())
        ncurses_include = ncurses_prefix / "include" / "ncursesw"
        ncurses_lib = ncurses_prefix / "lib"
        tmux_env = Environment()
        tmux_env.define("LIBTINFO_CFLAGS", f"-I{ncurses_include}")
        tmux_env.define("LIBTINFO_LIBS", f"-L{ncurses_lib} -ltinfow")
        tmux_env.define("LIBNCURSESW_CFLAGS", f"-I{ncurses_include}")
        tmux_env.define(
            "LIBNCURSESW_LIBS", f"-L{ncurses_lib} -lncursesw -ltinfow"
        )
        autotools = Autotools(self)
        with tmux_env.vars(self).apply():
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
        copy(
            self,
            "COPYING",
            src=self._ncurses_source_folder(),
            dst=os.path.join(self.package_folder, "licenses", "ncurses"),
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
