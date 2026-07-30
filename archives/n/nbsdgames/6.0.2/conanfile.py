#!/usr/bin/env python3
"""Conan recipe — nbsdgames 6.0.2 (Makefile).

Depends on ncurses/6.5 (Conan package) for terminal UI.
"""

import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class NbsdgamesConan(ConanFile):
    name = "nbsdgames"
    version = "6.0.2"
    description = "Text-based modern games — a collection of 21 terminal games"
    license = "Public-Domain"
    homepage = "https://github.com/abakh/nbsdgames"
    url = "https://github.com/abakh/nbsdgames"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("ncurses/6.5")

    def validate(self):
        # R32: Use `in ("Linux", "OHOS")` for settings.os check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"nbsdgames supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    def _make_arguments(self):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        cc = executables.get("c", "clang")

        # Conan ncurses/6.5 provides headers/libs via PKG_CONFIG_PATH
        platform_cflags = "-D_DEFAULT_SOURCE" if str(self.settings.os) == "OHOS" else ""
        widechar_flag = "-DNCURSES_WIDECHAR"

        cflags = " ".join(
            flag
            for flag in [
                platform_cflags,
                widechar_flag,
            ]
            if flag
        )

        return {
            "cc": cc,
            "cflags": cflags,
        }

    def build(self):
        apply_conandata_patches(self)
        source_dir = shlex.quote(self.source_folder)
        make_args = self._make_arguments()

        self.run(
            f"make -C {source_dir} "
            f"CC={shlex.quote(make_args['cc'])} "
            f"CFLAGS+={shlex.quote(make_args['cflags'])} -j1"
        )

    def package(self):
        prefix = shlex.quote(self.package_folder)
        source_dir = shlex.quote(self.source_folder)
        make_args = self._make_arguments()
        self.run(
            " ".join(
                [
                    f"make -C {source_dir} install",
                    f"CC={shlex.quote(make_args['cc'])}",
                    f"CFLAGS+={shlex.quote(make_args['cflags'])}",
                    f"GAMES_DIR={prefix}/bin",
                    f"SCORES_DIR={prefix}/var/games",
                    f"MAN_DIR={prefix}/share/man",
                ]
            )
        )
        self.run(f"make -C {source_dir} manpages MAN_DIR={prefix}/share/man/man6")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
