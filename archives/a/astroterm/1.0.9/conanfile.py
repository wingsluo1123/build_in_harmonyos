#!/usr/bin/env python3
"""Conan recipe for astroterm 1.0.9 — Meson project.

astroterm is a terminal-based star map written in C, displaying real-time
positions of stars, planets, and constellations. Upstream uses the Meson build
system and depends on argtable3, ncurses, and the math library.

R26: Terminal tools must be statically linked for DevBox deployment.
R27: argtable3 and ncurses are system libraries (no Conan recipe in repo).
"""
import os

from conan import ConanFile
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.files import get, replace_in_file
from conan.tools.layout import basic_layout
from conan.errors import ConanInvalidConfiguration


class AstrotermConan(ConanFile):
    name = "astroterm"
    version = "1.0.9"
    description = (
        "A terminal-based star map written in C, displaying real-time positions "
        "of stars, planets, and constellations"
    )
    license = "MIT"
    homepage = "https://github.com/da-luce/astroterm"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported"
            )

    def requirements(self):
        # R27: argtable3 and ncurses are system runtime libraries (no Conan recipe).
        # They are assumed to be available in the build environment.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # Inject ar/ranlib paths (CI profile may not provide them)
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = ce.get("ar")
        ranlib = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                cand = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(cand):
                    ar = cand
                    rlc = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(rlc):
                        ranlib = rlc
        if ar:
            tc.project_options["ar"] = ar
        if ranlib:
            tc.project_options["ranlib"] = ranlib
        tc.generate()

    def build(self):
        # Patch 1: Add stddef.h before string.h to fix size_t not found on OHOS
        replace_in_file(
            self,
            os.path.join(self.source_folder, "include", "parse_BSC5.h"),
            "#include <string.h>",
            "#include <stddef.h>\n#include <string.h>",
        )
        # Patch 2: Fix embed.sh for toybox xxd (doesn't support -i option)
        embed_sh = os.path.join(self.source_folder, "scripts", "embed.sh")
        replace_in_file(
            self,
            embed_sh,
            'if ! command -v xxd > /dev/null 2>&1; then\n    echo "Error: xxd is not installed or not found in PATH."\n    exit 1\nfi\n',
            "",
        )
        replace_in_file(
            self,
            embed_sh,
            "# Generate the header file",
            '# Fallback to Python embed.py if xxd does not support -i (e.g. toybox xxd)\n'
            'if ! command -v xxd > /dev/null 2>&1 || ! xxd -i /dev/null > /dev/null 2>&1; then\n'
            '    python3 "$(dirname "$0")/embed.py" --source "$SOURCE" --header "$HEADER" --array-name "$ARRAY_NAME"\n'
            '    exit $?\n'
            'fi\n'
            '\n'
            '# Generate the header file',
        )
        meson = Meson(self)
        meson.configure()
        meson.compile()

    def package(self):
        meson = Meson(self)
        meson.install()
        # R26: avoid shipping shared libraries for terminal tools
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            for root, _dirs, files in os.walk(lib_dir):
                for f in files:
                    if f.endswith(".so") or f.endswith(".so.1") or f.endswith(".la"):
                        os.remove(os.path.join(root, f))

    def package_info(self):
        self.cpp_info.libs = ["astroterm"]
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "ncurses", "argtable3"]
