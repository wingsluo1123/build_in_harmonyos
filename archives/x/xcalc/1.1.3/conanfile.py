#!/usr/bin/env python3
"""Conan recipe for X.Org xcalc 1.1.3 (X11 scientific calculator).

xcalc is a small X Athena-widget application: an RPN/infix calculator drawn
with Xaw Form/Label/Command/Toggle widgets.  Three C sources (actions.c,
math.c, xcalc.c) plus xcalc.h; autotools build (configure + make), no upstream
test suite.

Link/header dependencies come from the published ohpcd X11 stack (verified by
``conan list -r=ohpcd``): libxaw/1.0.14 (component xaw7), libxmu/1.3.1.1,
libxt/1.3.1, libxext/6.4.0.1, libx11/1.8.13 and xorgproto/2025.1 (xproto).
Upstream's configure.ac runs::

    PKG_CHECK_MODULES(XCALC, [xaw7 xt x11 xproto >= 7.0.22])
    PKG_CHECK_MODULES(APPDEFS, xt)

so the .pc module names must be xaw7/xt/x11/xproto.  PkgConfigDeps supplies
those names from the Conan metadata; libxmu publishes its Xmu component under
"libxmu" and xorgproto has no pkg_config_name, so both are renamed at the
consumer (same convention libxaw/1.0.14 and xfontsel/1.1.2 use).

OHOS/aarch64 native build=host notes (iron rule #0: no --build/--host/--target):

  * the bundled config.guess (2024-07-27) does not recognize ``uname -s
    HarmonyOS`` and probes the build compiler through $TMPDIR, which fails on
    HMFS.  patches/0001 teaches it to emit aarch64-unknown-linux-ohos (the
    bundled config.sub already accepts linux-ohos, so no config.sub patch).
  * autoconf 2.72's generated configure aborts with "working directory cannot
    be determined" when HMDFS cannot resolve getcwd() through the Conan cache
    parent chain, and config.status creates ./confXXXXXX with umask 077 (not
    writable on HMFS).  patches/0002 adds a $PWD fallback and relaxes that umask
    (E011/E114, same treatment as xfontsel/xhost/xwininfo).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XcalcConan(ConanFile):
    name = "xcalc"
    version = "1.1.3"
    description = "X.Org xcalc — scientific calculator for the X Window System"
    license = "X11"
    homepage = "https://gitlab.freedesktop.org/xorg/app/xcalc"
    url = "https://gitlab.freedesktop.org/xorg/app/xcalc"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xcalc supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # Pinned on the libxmu/1.3.1.1 + libxaw/1.0.14 track (libx11/1.8.13
        # force, libxext/6.4.0.1) — the same graph libxaw is published with.
        self.requires(
            "libx11/1.8.13", force=True, transitive_headers=True, transitive_libs=True
        )
        self.requires("libxext/6.4.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxt/1.3.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxmu/1.3.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxaw/1.0.14", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)
        # Runtime closure of the linked X11 libraries (libXaw7/libXt/libXmu
        # DT_NEEDED pull libX11 → libxcb → libXau/libXdmcp).  run=True only
        # injects their libdirs into the test_package conanrun environment.
        self.requires("libxcb/1.17.0", run=True)
        self.requires("libxau/1.0.11", run=True)
        self.requires("libxdmcp/1.1.5", run=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pkg_config = PkgConfigDeps(self)
        # Upstream PKG_CHECK_MODULES asks for the X.Org module spellings.
        # libxmu publishes the Xmu component as "libxmu"; xorgproto has no
        # pkg_config_name (it would default to "xorgproto").  Rename both at
        # the consumer so configure finds xmu.pc / xproto.pc.
        pkg_config.set_property("libxmu::xmu", "pkg_config_name", "xmu")
        pkg_config.set_property("xorgproto", "pkg_config_name", "xproto")
        pkg_config.generate()

        toolchain = AutotoolsToolchain(self)
        # Keep app-defaults under the package prefix (the xt.pc shipped by the
        # Conan dependency carries no `appdefaultdir` variable, so the
        # auto-detected value would be empty and install would target "/").
        toolchain.configure_args.append("--with-appdefaultdir=/share/X11/app-defaults")
        toolchain.generate()

    def _pkg_config_path(self):
        """PKG_CONFIG_PATH: generated .pc first, then dependency .pc dirs."""
        paths = [self.generators_folder]
        for dep in self.dependencies.values():
            package_folder = dep.package_folder
            if not package_folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                directory = libdir if os.path.isabs(libdir) else os.path.join(package_folder, libdir)
                pc_dir = os.path.join(directory, "pkgconfig")
                if os.path.isdir(pc_dir):
                    paths.append(pc_dir)
            for sub in ("share/pkgconfig", "lib/pkgconfig"):
                pc_dir = os.path.join(package_folder, sub)
                if os.path.isdir(pc_dir):
                    paths.append(pc_dir)
        previous = os.environ.get("PKG_CONFIG_PATH", "")
        if previous:
            paths.append(previous)
        return os.pathsep.join(dict.fromkeys(paths))

    def build(self):
        apply_conandata_patches(self)

        # HMDFS: the Conan cache parent path is not resolvable via getcwd();
        # run configure from the build folder and keep the logical PWD.
        try:
            os.chdir(self.build_folder)
        except OSError:
            self.output.warning("chdir(build_folder) failed; relying on PWD fallback")
        os.environ["PWD"] = self.build_folder

        previous = os.environ.get("PKG_CONFIG_PATH")
        os.environ["PKG_CONFIG_PATH"] = self._pkg_config_path()
        self.output.info(f"PKG_CONFIG_PATH={os.environ['PKG_CONFIG_PATH']}")
        try:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
            # Upstream ships no tests: Makefile.am declares bin_PROGRAMS + the
            # man subdir only (no TESTS/check_PROGRAMS/check-local) and
            # meson.build has no test().  The Automake `check` target is still
            # run so the empty suite is executed explicitly.
            autotools.make(target="check", args=["-j1"])
        finally:
            if previous is None:
                os.environ.pop("PKG_CONFIG_PATH", None)
            else:
                os.environ["PKG_CONFIG_PATH"] = previous

        self.output.info(
            'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
            '"framework":"Automake/Meson",'
            '"command":"make check",'
            '"discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,'
            '"reason":"xcalc 1.1.3 upstream ships no automated tests: '
            'Makefile.am has no TESTS/check_PROGRAMS/check-local, meson.build '
            'has no test(), and the release tarball contains no tests/ dir"}'
        )

    def _sign_elf(self, path):
        """OHOS refuses to execute an unsigned ELF (E077)."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool):
            self.run(f'"{objcopy}" --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'"{sign_tool}" sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass  # HMFS may not support chmod (HMBS_CAP_CHMOD=0)

    def package(self):
        Autotools(self).install()
        binary = os.path.join(self.package_folder, "bin", "xcalc")
        if os.path.isfile(binary):
            self._sign_elf(binary)
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # Command-line tool: only bin/ is exposed (R38).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
