#!/usr/bin/env python3
"""Conan recipe for coturn 4.7.0-r0 (TURN/STUN server)."""

import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps


class CoturnConan(ConanFile):
    name = "coturn"
    version = "4.7.0-r0"
    package_type = "application"

    description = "Free open source implementation of TURN and STUN Server"
    license = "BSD-3-Clause"
    homepage = "https://github.com/coturn/coturn"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "gen"

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("libevent/2.1.12")
        self.requires("sqlite3/3.49.1")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-shared",
            "--enable-static",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        tmpdir = os.path.join(os.environ.get("HOME", "/storage/Users/currentUser"), ".ci_logs", "coturn-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            replace_in_file(self, configure, "/var/tmp", tmpdir)
            replace_in_file(self, configure, "/tmp", tmpdir)
        # Get libevent paths from dependency for EVENT_CFLAGS/EVENT_LIBS
        # (configure skips pkg-config check when these are set, avoids libevent_openssl not found)
        event_cflags = ""
        event_libs = ""
        if "libevent" in self.dependencies:
            dep = self.dependencies["libevent"]
            if dep.cpp_info.includedirs:
                event_cflags = "-I" + dep.cpp_info.includedirs[0]
            if dep.cpp_info.libdirs:
                event_libs = "-L" + dep.cpp_info.libdirs[0]
            event_libs += " -levent -levent_extra -levent_pthreads"
        self.run(
            f'CONFIG_SHELL="${{CONFIG_SHELL:-/bin/sh}}" TMPDIR="{tmpdir}" TMP="{tmpdir}" '
            f'EVENT_CFLAGS="{event_cflags}" EVENT_LIBS="{event_libs}" '
            f'TURN_NO_TLS=1 '
            f'./configure --prefix=/ --bindir=${{prefix}}/bin --sbindir=${{prefix}}/bin '
            f'--libdir=${{prefix}}/lib --includedir=${{prefix}}/include --oldincludedir=${{prefix}}/include '
            f'--disable-shared --enable-static',
            env="conanbuild",
        )
        autotools = Autotools(self)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        # Set runenv so consumers (test_package) can find dependency shared libs
        for dep_name, dep in self.dependencies.items():
            if dep.cpp_info.libdirs:
                for libdir in dep.cpp_info.libdirs:
                    if os.path.isdir(libdir):
                        self.runenv_info.prepend_path("LD_LIBRARY_PATH", libdir)