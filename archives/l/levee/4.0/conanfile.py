#!/usr/bin/env python3
"""Conan recipe — levee 4.0 (David L Parsons' vi clone) for HarmonyOS PC.

Build system: configure.sh + configure.inc (the author's shell autoconf
emulator) generate config.h and Makefile from Makefile.in; no autotools.

OHOS adaptation (details and evidence in notes.md):
- the terminal layer uses the termcap interface (tgetent/tgetstr/tgoto) of
  Conan ncurses/6.6, a static wide-character libncursesw (R26); configure
  receives it through CFLAGS/LDFLAGS/LIBS and must detect it (USE_TERMCAP
  without the builtin TERMCAP_EMULATION fallback), which build() asserts;
- configure.sh compiles *and executes* helper programs on the build machine
  (config.sed for every AC_SUB, then make runs mkversio to write version.c).
  The compiler is therefore driven as "<cc> -static-pie": the helpers and the
  delivered editor are static PIEs without PT_INTERP, so they run natively on
  an AArch64 HarmonyOS host and through qemu-aarch64 binfmt on an x86_64 build
  machine, where /lib/ld-musl-aarch64.so.1 does not exist (ren 1.0 precedent);
- patches: 0001 renames levee globals that collide with curses symbols
  (duplicate symbols against the static library), 0002 adds --version/--help,
  0003 makes temporary files follow $TMPDIR (/tmp is read-only on HarmonyOS
  PC) and fixes a logit() call in the builtin glob used with musl.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
)
from conan.tools.layout import basic_layout


class LeveeConan(ConanFile):
    name = "levee"
    version = "4.0"
    description = "Levee, a small screen-oriented vi clone with visual and exec modes"
    license = "LicenseRef-levee"
    homepage = "https://github.com/Orc/levee"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("editor", "vi", "terminal", "cli")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # Pure C program: C++ settings do not affect the binary.
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"levee supports Linux/OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        # Static wide-character ncurses (R26: no system-named .so is produced).
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _ncurses_flags(self):
        ncurses = self.dependencies["ncurses"]
        info = ncurses.cpp_info.aggregated_components()
        if "ncursesw" not in info.libs:
            raise ConanException(
                f"ncurses/6.6 does not provide libncursesw (libs: {info.libs})"
            )

        def absolute(path):
            return path if os.path.isabs(path) else os.path.join(ncurses.package_folder, path)

        includes = [f"-I{absolute(d)}" for d in info.includedirs]
        libdirs = [f"-L{absolute(d)}" for d in info.libdirs]
        return includes, libdirs

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        includes, libdirs = self._ncurses_flags()

        # configure.sh reads CC/CFLAGS/LDFLAGS/LIBS from its environment and
        # writes them into the Makefile.  -static-pie sits in CC because the
        # config.sed helper is built with "$CC -o config.sed" only.
        configure_env = {
            "CC": f"{cc} -static-pie",
            "CFLAGS": " ".join(["-O2", "-fPIE"] + includes),
            "LDFLAGS": " ".join(libdirs),
            "LIBS": "-lncursesw",
        }
        assignments = " ".join(
            f"{key}={shlex.quote(value)}" for key, value in configure_env.items()
        )
        # --partial-install: do not add the "lv" alias, which clashes with the
        # unrelated lv pager.
        self.run(f"{assignments} bash ./configure.sh --partial-install", cwd=src)

        config_h = load(self, os.path.join(src, "config.h"))
        if "#define USE_TERMCAP 1" not in config_h or "TERMCAP_EMULATION" in config_h:
            raise ConanException(
                "configure did not detect the termcap API of libncursesw "
                "(see config.log)"
            )

        self.run("make -j1", cwd=src)

    def package(self):
        src = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(mandir, exist_ok=True)
        # Same names as upstream "make install": lev -> bin/levee, lv.1 -> levee.1
        # (make install would run "install -s" with the build machine's strip).
        shutil.copy2(os.path.join(src, "lev"), os.path.join(bindir, "levee"))
        shutil.copy2(os.path.join(src, "lv.1"), os.path.join(mandir, "levee.1"))
        copy(self, "COPYRIGHT", src=src, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README", src=src,
             dst=os.path.join(self.package_folder, "share", "doc", "levee"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
