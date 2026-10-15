#!/usr/bin/env python3
"""Conan recipe for run-parts 5.23.2 (Debian debianutils, run-parts only).

The debianutils tarball ships configure.ac/Makefile.am but no generated
`configure`, and its Makefile.am forces `SUBDIRS = po4a` (man page translation
fails with `po4a-translate not installed ... exit 1`). run-parts is a single C
file, so the recipe bypasses autotools and compiles it directly, supplying the
macros that config.h would normally provide:
  PACKAGE_VERSION   upstream acinclude.m4 DEBIANUTILS_VERSION (still "5.23.1"
                    inside the 5.23.2 tarball, so `run-parts --version` prints 5.23.1)
  HAVE_GETOPT_H     AC_CHECK_HEADERS(getopt.h)
  _FILE_OFFSET_BITS AC_SYS_LARGEFILE

The binary is linked static-pie: run-parts has no system-name library
dependency, and a static binary can be executed on a non-OHOS runner via
qemu-user (see test_package).
"""
import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)
from conan.tools.layout import basic_layout


class RunPartsConan(ConanFile):
    name = "run-parts"
    version = "5.23.2"
    description = "Debian run-parts: run all executable scripts in a directory"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/debian/debianutils"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler comes from the Conan profile, never from shell variables.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        defines = ("-DPACKAGE_VERSION='\"5.23.1\"' -DHAVE_GETOPT_H -DHAVE_PATHS_H "
                   "-D_FILE_OFFSET_BITS=64")
        flags = "-O2 -fPIE -fstack-protector-strong"
        ldflags = "-static-pie -s -Wl,-z,relro,-z,now,-z,noexecstack"
        self.run(f"{cc} {flags} {defines} {self.source_folder}/run-parts.c "
                 f"-o run-parts {ldflags}")

    def package(self):
        copy(self, "run-parts", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "run-parts.8", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "copyright", src=os.path.join(self.source_folder, "debian"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
