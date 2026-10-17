#!/usr/bin/env python3
"""Conan recipe — meterec 0.9.3 — console multi-track JACK recorder.

meterec is a console based multi track digital peak meter and recorder for
JACK, by Fabrice Lebas. Source: https://sourceforge.net/projects/meterec/
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout


class MeterecConan(ConanFile):
    name = "meterec"
    version = "0.9.3"
    description = "Console based multi track digital peak meter and recorder for JACK"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/meterec/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("meterec is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # configure.in hard requirements (PKG_CHECK_MODULES, verified against
        # the source tarball):
        self.requires("jack/1.9.22")         # PKG_CHECK_MODULES(JACK, [jack >= 1.9.7])
        self.requires("libsndfile/1.2.2")    # PKG_CHECK_MODULES(SNDFILE, [sndfile >= 1.0.25])
        self.requires("libconfig/1.8.2")     # PKG_CHECK_MODULES(LIBCONFIG, [libconfig >= 1.3.2])
        # configure.in: PKG_CHECK_MODULES(NCURSES, [ncurses >= 5.9]). The
        # repository ncurses package publishes the wide library only
        # (ncursesw.pc); 0001-configure-ncursesw.patch points the probe at
        # ncursesw, whose ABI is the superset the sources use.
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Pass the cross triplet explicitly: `uname -s` reports "HarmonyOS"
        # on the OHOS worker, which the bundled 2004-era configure does not
        # know. The tarball ships no config.sub/config.guess files; the
        # autoconf 2.59 generated script falls back to accepting the
        # explicit --host/--build values verbatim (verified: configure
        # accepts aarch64-unknown-linux-ohos with no config.sub present).
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
        ])
        tc.generate()
        # AutotoolsDeps supplies the pkg-config files (jack.pc, sndfile.pc,
        # libconfig.pc, ncursesw.pc) that configure's PKG_CHECK_MODULES
        # probes consume.
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # -j1: 2004-era automake tree; keep the build deterministic.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # Installs bin/meterec, bin/test (upstream queue self-test),
        # bin/meterec-init-conf and the man pages.
        # -j1: the OHOS worker forbids the make jobserver's mkfifo
        # (Operation not permitted) and is under fork() pressure; a serial
        # install avoids `jobserver mkfifo ... Operation not permitted` +
        # `fork: Resource temporarily unavailable` (same class of fix as vfu).
        autotools.install(args=["-j1"])

    def package_info(self):
        # Command-line application; exports no libraries for consumers.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
