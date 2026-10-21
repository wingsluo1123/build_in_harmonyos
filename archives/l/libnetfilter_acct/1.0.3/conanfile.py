#!/usr/bin/env python3
"""Conan recipe — libnetfilter_acct 1.0.3 (Autotools)

libnetfilter_acct is the userspace library for the netfilter extended
accounting infrastructure (the library behind the `nfacct` command).  It is a
thin object/attribute layer on top of libmnl: every message it builds is an
nfnetlink ACCT message assembled through libmnl, so libmnl is a hard build and
link dependency (upstream `configure.ac` line 19:
`PKG_CHECK_MODULES([LIBMNL], [libmnl >= 1.0.0])`).

Delivery decisions
------------------
* Static-only (`--enable-static --disable-shared`).  Same rationale as the
  netfilter siblings already in this repository (libmnl/1.0.5,
  libnfnetlink/1.0.2): upstream `configure.ac` calls `AC_DISABLE_STATIC`, so
  `--enable-static` has to be passed explicitly to get an archive at all; and
  libmnl itself ships static-only, while on HarmonyOS CMake injects no
  RPATH/RUNPATH for imported shared libraries.  A shared libnetfilter_acct
  would therefore leave out-of-tree consumers without any runtime search path
  for libmnl.
* Upstream has no automated test suite and no `TESTS` runner.  `make check`
  recurses into `examples/` and compile+links the three `check_PROGRAMS`
  (nfacct-get, nfacct-add, nfacct-del) against `libnetfilter_acct.la`, so that
  compile+link pass is the upstream verification entry point and is wired into
  `build()` (see test_package/MANIFEST.yml for the census).
* `package()` drops the libtool `.la` files: they bake absolute libdir paths
  into the package and make downstream libtool look in `//lib`.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibnetfilterAcctConan(ConanFile):
    name = "libnetfilter_acct"
    version = "1.0.3"
    description = "Userspace library for the netfilter extended accounting infrastructure"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.netfilter.org/projects/libnetfilter_acct/"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Mandatory: configure.ac does PKG_CHECK_MODULES([LIBMNL], [libmnl >= 1.0.0])
        self.requires("libmnl/1.0.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Upstream configure discovers libmnl through PKG_CHECK_MODULES, so the
        # dependency has to be visible as a .pc file.  PkgConfigDeps writes
        # libmnl.pc into the generators folder; AutotoolsToolchain prepends that
        # same folder to PKG_CONFIG_PATH in the conanbuild environment.
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # Upstream verification entry point: no TESTS runner upstream, but
        # `make check` builds examples/ check_PROGRAMS against the library.
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["netfilter_acct"]
