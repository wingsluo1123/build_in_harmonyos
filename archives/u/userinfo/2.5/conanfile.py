#!/usr/bin/env python3
"""Conan recipe for userinfo 2.5 - local user information gatherer.

``ui`` (Userinfo) is a small console utility that prints a variety of fields
about one or more local users.  Its functionality lives in loadable modules
(``passwd.so``, ``mail.so``, ``login.so``) which the program locates through the
RUNPATH baked in at build time.

The build uses the release's pre-generated autotools files (``configure`` +
``Makefile.in`` + libtool), so no autoreconf is needed.

OHOS notes
----------
* The autoconf ``config.status`` scratch directory is created with
  ``umask 077`` (mode 0700).  HMDFS refuses to create files inside a directory
  that is not group/other-traversable, so the scratch step fails with
  "Permission denied".  Patch 0001 relaxes that umask to 022.
* Explicit ``--build/--host/--target`` triplets avoid the ancient
  ``config.guess``/``config.sub`` in ``build/`` (they predate HarmonyOS), and
  ``--program-prefix=`` keeps the installed program named ``ui``.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

_GNU_TRIPLET = "aarch64-unknown-linux-gnu"


class UserinfoConan(ConanFile):
    name = "userinfo"
    version = "2.5"
    description = "Userinfo: console utility that displays information about a local user"
    license = "GPL-2.0-or-later"
    homepage = "http://userinfo.sourceforge.net/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "userinfo OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler("c", "clang")
        opt = "-O2" if str(self.settings.build_type) == "Release" else "-g -O0"
        t = _GNU_TRIPLET
        self.run(
            'CC="{cc}" CFLAGS="-Wall {opt}" sh ./configure '
            '--build={t} --host={t} --target={t} --program-prefix= '
            '--prefix="{prefix}"'.format(cc=cc, opt=opt, t=t,
                                         prefix=self.package_folder),
            cwd=self.source_folder)
        # Keep the generated autotools files newer than their sources so make
        # does not try to re-run aclocal/automake (maintainer mode).
        self.run('touch aclocal.m4 configure config.h.in Makefile.in '
                 'src/Makefile.in src/modules/Makefile.in doc/Makefile.in '
                 'contrib/Makefile.in', cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        self.run("make install", cwd=self.source_folder)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []
