#!/usr/bin/env python3
"""Conan recipe for xine 0.99.14 — the upstream project is named xine-ui.

This package is called `xine` (matching its archive directory and the delivery
branch), while "xine-ui" below always refers to the upstream project name, the
tarball and the strings/files upstream emits (xine-ui.xml, share/xine-ui/).

xine-ui is the "xine" application built on the libxine engine (sibling package
xine-lib/1.2.13). It installs three executables (xine, xine-check,
xine-bugreport) plus skins, icons, desktop/mime entries and man pages.

Upstream registers no automated test suite: "make check" is a no-op in every
one of the 20 recursive check directories (no TESTS=, no check_PROGRAMS). The
real upstream test entries are the two EXTRA_PROGRAMS that automake only builds
on request — src/xitk/session_ctrl (from ctrl_test.c, talks to a running xine
session over $HOME/.xine/session.N) and src/xitk/xine-toolkit/test (a stale xitk
widget gallery that no longer matches the headers in this tarball). build()
compiles session_ctrl; see notes.md for why it cannot be executed on OHOS.

OHOS adaptations (see patches/ and notes.md):
  * config.guess / config.sub do not know aarch64-*-HarmonyOS.
  * configure's XINE_MIME and misc/desktops assume a plugindir pkg-config
    variable that the Conan-synthesised libxine.pc does not carry.
  * --without-fb: src/fb/keys.c calls pthread_cancel()/pthread_testcancel(),
    which the OHOS libc does not provide, and there is no framebuffer console.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XineConan(ConanFile):
    name = "xine"
    version = "0.99.14"
    description = "xine-ui — the X11 front-end (media player) for the libxine engine"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/xine/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Player application, not a library (R38: commands.json at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Media engine; provides the libxine pkg-config module.
        self.requires("xine-lib/1.2.13")
        # X11 output/extension support probed by configure. Pinned to the
        # libx11/6.4.0 + libxext/6.4.0 family because libxv/libxinerama/
        # libxxf86vm/libxtst/libxscrnsaver in the registry all require exactly
        # those versions (the 1.8.13 line is not referenced by any extension).
        self.requires("libx11/6.4.0")
        self.requires("libxext/6.4.0")
        self.requires("libxv/1.0.13")
        self.requires("libxinerama/1.1.5")
        self.requires("libxxf86vm/1.1.5")
        self.requires("libxtst/1.2.5")
        self.requires("libxscrnsaver/1.2.5")
        # Skin/loader image decoding and the http/ftp MRL access.
        self.requires("libpng/1.6.58")
        self.requires("libjpeg-turbo/3.2.0.1")
        self.requires("curl/8.15.0.1")

    def validate(self):
        # R32: platform checks must accept OHOS, not just Linux.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xine-ui is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        pkg = PkgConfigDeps(self)
        pkg.generate()

        tc = AutotoolsToolchain(self)
        # The framebuffer front-end cannot build on OHOS: src/fb/keys.c uses
        # pthread_cancel()/pthread_testcancel(), which the OHOS libc does not
        # export, and there is no framebuffer console device to drive.
        tc.configure_args.append("--without-fb")
        # Message catalogs are off: AM_GNU_GETTEXT here decides USE_NLS by
        # probing for a preinstalled GNU gettext, which the OHOS toolchain does
        # not ship. Pinning it keeps po/ out of the build on every worker.
        tc.configure_args.append("--disable-nls")
        tc.generate()

        env = Environment()
        # Pin pkg-config to the Conan-generated modules so configure cannot
        # silently pick up a system X11/jpeg/png/curl instead of the graph.
        env.define("PKG_CONFIG_LIBDIR", self.generators_folder)
        # The OHOS runtime linker has no default search path for the Conan
        # cache, and configure/make run the conftest programs they just linked
        # ("Error loading shared library libxine.so.2" without this).
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        apply_conandata_patches(self)
        # E490: HMDFS extraction and patch application can drop the mode bits,
        # after which config.guess/configure fail with "Permission denied".
        self.run('for f in configure config.guess config.sub install-sh missing '
                 'compile depcomp ar-lib ltmain.sh; do if [ -f "$f" ]; then chmod +x "$f"; fi; done')
        autotools = Autotools(self)
        autotools.configure()
        # R9: single job — parallel make hits the HMDFS jobserver fifo EPERM.
        autotools.make(args=["-j1"])
        # Upstream test entries are EXTRA_PROGRAMS, so `make all` skips them and
        # `make check` is a no-op. -C enters the mirror build subdirectory, whose
        # generated Makefile carries the rule and the VPATH to the source.
        # src/xitk/session_ctrl (ctrl_test.c) is compiled and cross-checked here;
        # it is deliberately not executed, because its connect_to_session() calls
        # setreuid(), which the OHOS syscall policy rejects with SIGSYS (rc=159) —
        # see notes.md. The other entry, src/xitk/xine-toolkit/test, is dead
        # upstream code (stale Imlib/xitk APIs, no include path in its rule) and
        # needs an X display, so it is neither built nor run.
        self.run('make -j1 -C src/xitk session_ctrl')

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Standalone player: no headers or link flags to export, only bin/ (R38).
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
