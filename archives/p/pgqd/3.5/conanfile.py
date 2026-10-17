#!/usr/bin/env python3
"""Conan recipe for pgqd 3.5 on OpenHarmony (aarch64).

pgqd is the PgQ maintenance daemon: it keeps PgQ queues ticking and rotates
their tables.  It is the runtime half of the PgQ queue system and is deployed
as a long-running daemon, so the package ships a binary, not a library.

Upstream build notes
--------------------
* Upstream `make` links libpq directly (`-lpq`), and configure refuses to run
  without a `pg_config` on PATH.  libpq/18.6.1 ships that tool, so the recipe
  only has to make its `bin/` visible while configuring.
* libevent is discovered with `PKG_CHECK_MODULES(LIBEVENT, [libevent >= 2.0])`,
  hence PkgConfigDeps.
* The man page is rendered from README.rst with rst2man (docutils).  OHOS has
  no python3-docutils, so patch 0001 makes that step degrade gracefully while
  keeping the upstream behaviour wherever rst2man exists.
"""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class PgqdConan(ConanFile):
    name = "pgqd"
    version = "3.5"
    description = "PgQ maintenance daemon — keeps PgQ queues ticking and maintained"
    license = "ISC"
    homepage = "https://github.com/pgq/pgqd"
    url = "https://github.com/pgq/pgqd"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libevent/2.1.13")
        self.requires("libpq/18.6.1")

    def layout(self):
        # pgqd uses "antimake" — a plain hand-written Makefile chain, not
        # automake.  The toplevel Makefile pulls in lib/mk/antimake.mk by
        # relative path, so it must run from the source tree; an out-of-source
        # build (conan's default) fails with "No rule to make target
        # 'lib/mk/antimake.mk'".
        basic_layout(self, build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        env = tc.environment()
        # libevent is found through pkg-config: expose the .pc files conan just
        # generated for the dependencies.
        env.append_path("PKG_CONFIG_PATH", self.generators_folder)
        # configure does AC_PATH_PROGS(PG_CONFIG, pg_config) and hard-fails
        # without it; libpq/18.6.1 ships pg_config in its bin/.
        pg_bindirs = list(self.dependencies["libpq"].cpp_info.bindirs) or ["bin"]
        for bindir in pg_bindirs:
            env.append_path("PATH", os.path.join(self.dependencies["libpq"].package_folder, bindir))
        tc.generate(env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # -j1 on purpose: OHOS CI workers intermittently fail to fork under
        # load ("fork: retry: Resource temporarily unavailable").  A parallel
        # make multiplies that pressure and, worse, configure's feature probes
        # silently answer "no" when they cannot fork, which yields a config.h
        # that redefines pid_t/size_t as macros and breaks the compile.  A
        # serial build keeps the fork count low and stays reproducible.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # -j1 for the same reason as the build, and because this runs right
        # before test_package starts its PostgreSQL cluster.
        autotools.install(args=["-j1"])

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # pgqd links libpq/libevent from the dependency packages; make them
        # resolvable for consumers (test_package included).
        for dep in self.dependencies.host.values():
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", dep.cpp_info.libdirs)
