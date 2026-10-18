#!/usr/bin/env python3
"""Conan recipe for pingu 1.5.1 — ISP fail-over / policy routing daemon.

pingu is a small daemon that pings a set of hosts and reconfigures the
kernel routing table (policy routing rules, nexthop multipath) when an
uplink goes up or down.  It ships three executables:

  pingu     - the daemon (sbin)
  pinguctl  - administration client for the daemon's unix socket (sbin)
  mtu       - PMTU probe/injection helper (bin)

The upstream build is *not* autotools: ./configure is a hand written shell
script that probes strlcpy and libev and writes config.h + config.mk, and
the Makefiles are hand written too.  Only --prefix/--sysconfdir/... style
arguments are accepted, so the configure invocation is done explicitly
instead of through AutotoolsToolchain.configure().

Patches (see conandata.yml):
  0001  upstream probes pkg-config with "--exist"; the option is "--exists",
        so libev was only ever found through the implicit -lev fallback.
  0002  musl-derived sysroots (OpenHarmony) do not guard the kernel UAPI
        definition of struct sockaddr_storage the way glibc does, so the
        TUs that mix libc and netlink UAPI headers fail on redefinition.
"""
import os

from conan import ConanFile
from conan.tools.build import build_jobs
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class PinguConan(ConanFile):
    name = "pingu"
    version = "1.5.1"
    description = ("Small daemon that pings hosts and executes a script when their status "
                   "changes, with policy routing and ISP fail-over support")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ncopa/pingu"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # libev is a hard build/runtime requirement (configure dies without it).
        self.requires("libev/4.33")

    def generate(self):
        # Only the toolchain flags are used; ./configure is called manually
        # because it rejects every argument it does not know.
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        env = tc.environment()
        # configure locates libev through pkg-config (see patch 0001) and
        # compiles its probes in $TMPDIR, which is read-only on OpenHarmony.
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        env.define("TMPDIR", self.build_folder)
        tc.generate(env=env)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.run(
            "./configure"
            " --prefix=/usr"
            " --exec-prefix=/usr"
            " --sysconfdir=/etc"
            " --localstatedir=/var"
            " --disable-doc",
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.run(f"make -j{build_jobs(self)}", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # Upstream's "make install" relies on coreutils install(1), which is not
        # part of the OpenHarmony userland; the three binaries and the example
        # configuration are copied explicitly instead.
        bindir = os.path.join(self.package_folder, "bin")
        sbindir = os.path.join(self.package_folder, "sbin")
        copy(self, "mtu", src=os.path.join(self.source_folder, "src"), dst=bindir)
        copy(self, "pingu", src=os.path.join(self.source_folder, "src"), dst=sbindir)
        copy(self, "pinguctl", src=os.path.join(self.source_folder, "src"), dst=sbindir)
        copy(self, "pingu.conf", src=self.source_folder,
             dst=os.path.join(self.package_folder, "etc", "pingu"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # pingu/pinguctl live in sbin, mtu in bin; both must be on PATH for
        # consumers (and for test_package, which executes them).
        self.cpp_info.bindirs = ["bin", "sbin"]
