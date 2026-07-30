#!/usr/bin/env python3
"""Conan recipe for astroterm 1.0.9 — Meson project.

astroterm is a terminal-based star map written in C, displaying real-time
positions of stars, planets, and constellations. Upstream uses the Meson build
system and depends on argtable3, ncurses, and the math library.

R26: Terminal tools must be statically linked for DevBox deployment.
The OHOS build uses official cmd-pkgs ncurses because CI workers do not ship
the corresponding development headers.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout


class AstrotermConan(ConanFile):
    name = "astroterm"
    version = "1.0.9"
    description = (
        "A terminal-based star map written in C, displaying real-time positions "
        "of stars, planets, and constellations"
    )
    license = "MIT"
    homepage = "https://github.com/da-luce/astroterm"
    url = "https://github.com/da-luce/astroterm"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "*",
            src=os.path.join(self.recipe_folder, "res"),
            dst=os.path.join(self.export_sources_folder, "res"),
        )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        download(
            self,
            **self.conan_data["bsc5_source"],
            filename=os.path.join(self.source_folder, "data", "bsc5"),
        )
        get(
            self,
            **self.conan_data["argtable3_source"],
            destination=os.path.join(self.source_folder, "deps", "argtable3"),
            strip_root=True,
        )
        get(
            self,
            **self.conan_data["ncurses_ohos"],
            destination=os.path.join(self.source_folder, "deps", "ncurses-ohos"),
        )
        # Copy exported res/ (ncurses headers) into source folder so that
        # generate()/build() can reference res/ncurses/include consistently.
        copy(
            self,
            "*",
            src=os.path.join(self.export_sources_folder, "res"),
            dst=os.path.join(self.source_folder, "res"),
        )

    def generate(self):
        tc = MesonToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.project_options["default_library"] = "static"
        if self.settings.os == "OHOS":
            ncurses_include = os.path.join(
                self.source_folder, "res", "ncurses", "include"
            ).replace("\\", "/")
            # Upstream public headers expose curses types to targets that do
            # not depend directly on the Meson curses dependency.
            tc.extra_cflags.extend(
                [f"-I{ncurses_include}", "-DNCURSES_WIDECHAR"]
            )
        tc.generate()
        self._inject_meson_archiver()

    def _inject_meson_archiver(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar:
            compiler = executables.get("cpp") or executables.get("c") or ""
            bindir = os.path.dirname(compiler)
            candidate = os.path.join(bindir, "llvm-ar") if bindir else ""
            if candidate and os.path.isfile(candidate):
                ar = candidate
                candidate_ranlib = os.path.join(bindir, "llvm-ranlib")
                if os.path.isfile(candidate_ranlib):
                    ranlib = candidate_ranlib
        native_file = os.path.join(
            self.generators_folder, "conan_meson_native.ini"
        )
        if not ar or not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        binaries = "[binaries]\nar = '%s'\n" % ar
        if ranlib:
            binaries += "ranlib = '%s'\n" % ranlib
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content.replace("[binaries]\n", binaries, 1))

    def build(self):
        apply_conandata_patches(self)
        meson_file = os.path.join(self.source_folder, "meson.build")
        replace_in_file(
            self,
            meson_file,
            "argtable = dependency('argtable3', required: false)",
            "argtable = declare_dependency(\n"
            "        sources: files('deps/argtable3/src/argtable3.c'),\n"
            "        include_directories: include_directories('deps/argtable3/src'),\n"
            "    )",
        )
        if self.settings.os == "OHOS":
            ncurses_include = os.path.join(
                self.source_folder, "res", "ncurses", "include"
            )
            ncurses_library = os.path.join(
                self.source_folder,
                "deps",
                "ncurses-ohos",
                "lib",
                "libncursesw.a",
            )
            for required_path in (ncurses_include, ncurses_library):
                if not os.path.exists(required_path):
                    raise ConanInvalidConfiguration(
                        f"required OHOS ncurses asset missing: {required_path}"
                    )
            ncurses_library = ncurses_library.replace("\\", "/")
            replace_in_file(
                self,
                meson_file,
                "curses = dependency('curses', required : true)",
                "curses = declare_dependency(\n"
                "        include_directories: include_directories('res/ncurses/include'),\n"
                f"        link_args: ['{ncurses_library}'],\n"
                "    )",
            )
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        # R26: avoid shipping shared libraries for terminal tools
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            for root, _dirs, files in os.walk(lib_dir):
                for f in files:
                    if f.endswith((".so", ".la")) or ".so." in f:
                        os.remove(os.path.join(root, f))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
