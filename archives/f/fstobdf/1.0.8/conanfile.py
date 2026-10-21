#!/usr/bin/env python3
"""Conan recipe for fstobdf 1.0.8 (X.Org application) on HarmonyOS PC.

fstobdf reads a font from an X Font Server and writes the equivalent BDF file
to stdout, which is useful for testing servers, debugging font metrics and
reproducing lost BDF files.  It is a single C executable built by GNU
autotools: the release tarball ships a pre-generated `configure`, and the
program is assembled from chars.c / fstobdf.c / header.c / props.c plus one
man page.

configure.ac asks pkg-config for

    PKG_CHECK_MODULES(FSTOBDF, [xproto >= 7.0.25 x11 libfs])

so three pkg-config modules must resolve at configure time:
  * xproto   -- from xorgproto (>= 7.0.25; measured 7.0.34)
  * x11      -- from libx11, which also supplies X11/Xlib.h used by chars.c
  * libfs    -- from libfs, which supplies X11/fonts/FSlib.h and libFS.so.6

`PkgConfigDeps` writes generated .pc files for every dependency into the
generators folder and puts both that folder and each dependency's own
pkgconfig directory (including xorgproto's `share/pkgconfig`, which is where
xproto.pc / kbproto.pc / fontsproto.pc live) on PKG_CONFIG_PATH, so the
Requires: chains of the generated x11.pc/libfs.pc resolve without any extra
aliasing.  VirtualBuildEnv exports that path to configure.

Declared patches, applied for real in build():
  0001 config.guess HarmonyOS host detection
  0002 configure HMDFS pwd fallback plus HMDFS-safe config.status scratch dir

One deliberate omission, backed by measurement rather than by copying the
sibling X11 recipes: no config.sub patch.  This 1.0.8 tarball already accepts
`aarch64-unknown-linux-ohos` -- its OS whitelist carries `ohos*` and its
kernel-OS whitelist carries `linux-ohos*`, measured `rc=0`.

The 0002 `$PWD` fallback is needed by the clean-verify style build (a scratch
tree under $HOME whose parent becomes unreachable), where `pwd` aborts with
"cannot access parent directories" and configure dies with "working directory
cannot be determined".  A plain `conan create` from the Conan cache does not
hit it, so it is worth knowing that G0 and W3 fail for different reasons.
This is not the anti-pattern E386 forbids (accepting a pwd that wrote
diagnostics): the fallback only triggers when `pwd` fails outright.

Upstream ships no test suite (no tests/ directory, no TESTS/check_PROGRAMS in
any Makefile.am), so all test evidence comes from test_package/, which really
executes the installed binary.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, rm)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class FstobdfConan(ConanFile):
    name = "fstobdf"
    version = "1.0.8"
    description = ("fstobdf reads a font from an X Font Server through the FS "
                   "protocol client library and prints the equivalent BDF file")
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/app/fstobdf"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "fstobdf is an X Font Server client, supported on Linux and OHOS only"
            )

    def requirements(self):
        # libfs provides X11/fonts/FSlib.h, libFS.so.6 and libfs.pc.
        self.requires("libfs/1.0.10")
        # libx11 provides x11.pc and X11/Xlib.h (chars.c includes it directly).
        # 1.8.13 is the version the rest of the X11 app family resolves against
        # (libxt/1.3.1 pins it); 6.4.0 conflicts with that family.
        self.requires("libx11/1.8.13")
        # xorgproto provides xproto.pc (>= 7.0.25) and X11/Xosdefs.h.
        self.requires("xorgproto/2025.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # The OHOS worker has no /bin/sh worth using for configure: both
            # the outer shell and configure's CONFIG_SHELL are pointed at the
            # HNP bash, and the compiler family at the HNP clang so the
            # toolchain does not depend on whatever PATH the worker happens to
            # export (R33: values come from the Conan toolchain env, never
            # from bare ${CC}/${CFLAGS}).
            env = tc.environment()
            shell = "/data/service/hnp/bin/bash"
            env.define_path("SHELL", shell)
            env.define_path("CONFIG_SHELL", shell)
            env.define_path("CC", "/data/service/hnp/bin/clang")
            env.define_path("CXX", "/data/service/hnp/bin/clang++")
            env.define_path("LD", "/data/service/hnp/bin/ld.lld")
            env.define_path("AR", "/data/service/hnp/bin/llvm-ar")
            env.define_path("RANLIB", "/data/service/hnp/bin/llvm-ranlib")
            env.define_path("STRIP", "/data/service/hnp/bin/llvm-strip")
            env.define_path("NM", "/data/service/hnp/bin/llvm-nm")
        tc.generate()
        # PKG_CHECK_MODULES(FSTOBDF, xproto x11 libfs) needs xproto.pc,
        # x11.pc and libfs.pc at configure time.  PkgConfigDeps writes them
        # into the generators folder and also exposes each dependency's own
        # pkgconfig dirs, so the x11.pc -> xproto/kbproto and
        # libfs.pc -> xproto/fontsproto Requires: chains resolve too.
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # -j1 on purpose: GNU make's jobserver needs a FIFO under $HOME and
        # mkfifo is not permitted on this platform
        # ("make: jobserver mkfifo: ... Operation not permitted").
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        rm(self, "*.la", self.package_folder, recursive=True)
        rm(self, "*.o", self.package_folder, recursive=True)

    def package_info(self):
        # fstobdf is a command line tool: it installs bin/fstobdf and the
        # fstobdf.1 man page, with no headers and no libraries.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
