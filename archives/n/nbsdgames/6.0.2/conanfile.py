#!/usr/bin/env python3
"""Conan recipe — nbsdgames 6.0.2 (Makefile)."""

import os
import shlex

from conan import ConanFile
from conan.tools.files import export_conandata_patches, get
from conan.tools.layout import basic_layout


class NbsdgamesConan(ConanFile):
    name = "nbsdgames"
    version = "6.0.2"
    description = "Text-based modern games — a collection of 21 terminal games"
    license = "Public-Domain"
    homepage = "https://github.com/abakh/nbsdgames"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _make_arguments(self):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        cc = executables.get("c", "clang")

        dep = self.dependencies["ncurses"]
        include_flags = " ".join(f"-I{path}" for path in dep.cpp_info.includedirs)
        define_flags = " ".join(f"-D{value}" for value in dep.cpp_info.defines)
        extra_cflags = " ".join(dep.cpp_info.cflags)
        libdir_flags = " ".join(f"-L{path}" for path in dep.cpp_info.libdirs)
        libs = " ".join(f"-l{lib}" for lib in dep.cpp_info.libs)
        cflags = " ".join(flag for flag in [include_flags, define_flags, extra_cflags] if flag)

        return {
            "cc": cc,
            "cflags": cflags,
            "ldflags": libdir_flags,
            "libs": libs,
        }

    def build(self):
        source_dir = shlex.quote(self.source_folder)
        make_args = self._make_arguments()

        self.run(
            f"make -C {source_dir} "
            f"CC={shlex.quote(make_args['cc'])} "
            f"CFLAGS+={shlex.quote(make_args['cflags'])} "
            f"LDFLAGS+={shlex.quote(make_args['ldflags'])} "
            f"LIBS_PKG_CONFIG={shlex.quote(make_args['libs'])} -j1"
        )

    def package(self):
        prefix = self.package_folder
        source_dir = shlex.quote(self.source_folder)
        make_args = self._make_arguments()
        self.run(
            " ".join(
                [
                    f"make -C {source_dir} install",
                    f"CC={shlex.quote(make_args['cc'])}",
                    f"CFLAGS+={shlex.quote(make_args['cflags'])}",
                    f"LDFLAGS+={shlex.quote(make_args['ldflags'])}",
                    f"LIBS_PKG_CONFIG={shlex.quote(make_args['libs'])}",
                    f"GAMES_DIR={prefix}/bin",
                    f"SCORES_DIR={prefix}/var/games",
                    f"MAN_DIR={prefix}/share/man",
                ]
            )
        )
        self.run(f"make -C {source_dir} manpages MAN_DIR={prefix}/share/man/man6")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
