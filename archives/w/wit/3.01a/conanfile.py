#!/usr/bin/env python3
"""Conan recipe for wit 3.01a — Wiimms ISO Tools on HarmonyOS PC."""

import os
import shlex

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout

MAKEFILE_SETUP = """\
REVISION\t:= 7464
REVISION_NUM\t:= 7464
REVISION_NEXT\t:= 7464
BINTIME\t\t:= 1512259200
DATE\t\t:= 2017-12-03
TIME\t\t:= 00:00:00

FORCE_M32\t:= 0
HAVE_FUSE\t:= 0
HAVE_ZLIB\t:= 1
STATIC\t\t:= 0
DEFINES1\t:= -DHAVE_ZLIB=1 -DHAVE_POSIX_FALLOCATE=1

HAVE_INSTBIN\t:= 0
HAVE_INSTBIN_32\t:= 0
HAVE_INSTBIN_64\t:= 0

INSTALL_PATH\t:= /usr
INSTBIN\t\t:= /tmp
INSTBIN_32\t:= /tmp
INSTBIN_64\t:= /tmp

SYSTEM\t\t:= linux
SYSTEMID\t:= 0x5000000
SYSTEM_LINUX\t:= 1
"""


class WitConan(ConanFile):
    name = "wit"
    version = "3.01a"
    description = "Wiimms ISO Tools: command line tools to manipulate Wii and GameCube disc images"
    license = "GPL-2.0-only"
    homepage = "https://wit.wiimm.de/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("bzip2/1.0.8")
        self.requires("mhash/0.9.9.9")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, strip_root=True, **self.conan_data["sources"])

    def _cc(self):
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp_execs.get("c") or "clang"

    def build(self):
        apply_conandata_patches(self)
        save(self, os.path.join(self.source_folder, "Makefile.setup"), MAKEFILE_SETUP)
        zlib = self.dependencies["zlib"].cpp_info
        bzip2 = self.dependencies["bzip2"].cpp_info
        mhash = self.dependencies["mhash"].cpp_info
        include_flags = " ".join(
            f"-I{p}" for p in list(zlib.includedirs) + list(bzip2.includedirs) + list(mhash.includedirs)
        )
        lib_flags = " ".join(
            f"-L{p}" for p in list(zlib.libdirs) + list(bzip2.libdirs) + list(mhash.libdirs)
        )
        cc = self._cc()
        xflags = f"-fPIE {include_flags}"
        ldflags = f"-pie {lib_flags}"
        jobs = os.cpu_count() or 2
        shell = os.environ.get("SHELL", "")
        shell_arg = f" SHELL={shlex.quote(shell)}" if shell and os.path.exists(shell) else ""
        env = Environment()
        env.define("WIT_SETUP_SKIP", "1")
        with env.vars(self).apply():
            self.run(
                f"make wit wwt wdf -j{jobs}"
                f" CC={shlex.quote(cc)} STRIP=true"
                f" XFLAGS={shlex.quote(xflags)} LDFLAGS={shlex.quote(ldflags)}{shell_arg}",
                cwd=self.source_folder,
            )

    def package(self):
        for tool in ("wit", "wwt", "wdf"):
            copy(self, tool, self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "gpl-2.0.txt", self.source_folder,
             os.path.join(self.package_folder, "share", "licenses", "wit"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
