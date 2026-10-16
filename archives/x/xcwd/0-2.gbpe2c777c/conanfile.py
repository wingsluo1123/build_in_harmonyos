#!/usr/bin/env python3
"""Conan recipe for xcwd 0-2.gbpe2c777c — print the cwd of the focused X11 window.

xcwd is a single-file X11 client (``xcwd.c``) built by a hand-written Makefile.
The package product is the command-line executable ``bin/xcwd``, so this is an
"application" package (R38: a software-level ``commands.json`` is required).

OHOS adaptation notes (full record in notes.md):

  * The upstream Makefile selects its platform branch with
    ``UNAME:=$(shell uname)`` (Makefile:7).  HarmonyOS ``uname`` reports
    ``HarmonyOS``, which hits neither ``Linux`` nor ``FreeBSD`` and aborts at
    parse time::

        Makefile:20: *** Operating System not supported..  Stop.

    The recipe therefore passes ``UNAME=Linux`` on the make command line.  This
    is a *build-system variable* of the upstream Makefile, not a source patch:
    it selects upstream's own ``-DLINUX`` branch, which is the behaviourally
    correct one on OHOS (``/proc/<pid>/stat`` scanning via ``glob`` and
    ``/proc/<pid>/cwd`` via ``readlink``, both available under HarmonyOS
    bionic).  ``xcwd.c`` and the Makefile are left byte-identical to upstream
    (R8 / R2: no patch is declared in conandata.yml).

  * GNU make command-line variables override even ``+=``, so the Makefile's
    ``CFLAGS += -DLINUX`` (Makefile:14) is silently dropped once ``CFLAGS`` is passed on the
    command line.  ``CFLAGS`` is therefore restated in full: upstream's own
    ``-Wall -Wextra -std=gnu99 -O2`` plus ``-DLINUX`` plus the Conan include
    dirs.  Dropping ``-DLINUX`` here would produce a link-time-fine but
    feature-empty binary (both upstream branches define ``getProcesses`` /
    ``readPath``), which is exactly the silent failure this comment prevents.

  * Include/link paths come from the Conan dependency graph — ``libx11/6.4.0``
    and header-only ``xorgproto/2025.1`` (<X11/Xfuncproto.h>) — never from a
    shared prefix (R49) and never from bare shell variables (R33): the compiler
    is read from ``tools.build:compiler_executables`` and the flags are built
    from ``self.conf`` / ``cpp_info``.

  * No ``DT_RUNPATH`` is embedded.  The OHOS loader rejects RUNPATH entries that
    point into the user-writable Conan cache, and the house convention for X11
    packages in this repository (compare the packaged ``xsetroot`` binary) is to
    let the ``conanrun`` environment provide the library search path.

  * ``package()`` copies the built binary instead of driving upstream's
    ``install`` target: that rule is ``install -m 0755 ${EXE} $(prefix)/bin``
    with no ``DESTDIR`` support, so it cannot install into the Conan package
    folder without pointing ``prefix`` at it, and Conan owns the isolation
    (R20: DESTDIR staging deprecated).

Upstream ships **no test suite** (the tree is 5 files, the Makefile has no
``check`` target and no test sources exist), so per TEST_QUALITY_SPEC the
consumer suite in ``test_package/`` is the adapted test coverage; MANIFEST.yml
declares that explicitly with the census evidence.
"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Dependencies whose include/lib dirs the Makefile compile+link lines need.
# xorgproto is header-only and supplies <X11/Xfuncproto.h>, pulled in by
# <X11/Xlib.h>.
DEPENDENCY_FLAG_SOURCES = ("libx11", "xorgproto")

# Upstream Makefile line 3-4 defaults, restated because a command-line CFLAGS
# overrides the makefile *and* its conditional `CFLAGS += -DLINUX`.
UPSTREAM_CFLAGS = "-Wall -Wextra -std=gnu99 -O2"


class XcwdConan(ConanFile):
    name = "xcwd"
    version = "0-2.gbpe2c777c"
    description = ("Print the current working directory of the focused X11 "
                   "window (X current working directory)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/schischi/xcwd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("x11", "xorg", "cwd", "utility")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # conandata.yml carries the pinned source URL + sha256; patches/ is empty by
    # design, but export_conandata_patches() keeps the recipe shape identical to
    # its siblings (and picks the directory up automatically if one is ever added).
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

    # R32: HarmonyOS must be matched together with Linux, not instead of it.
    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xcwd supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler from Conan conf, never from a bare shell variable.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        include_flags, lib_dirs = self._dependency_flags()
        cflags = " ".join([UPSTREAM_CFLAGS, "-DLINUX", *include_flags])
        ldflags = " ".join([*lib_dirs, "-lX11"])

        # Upstream's Makefile has no out-of-source support: it compiles and links
        # in the source tree, so the build runs there (R9: always -j1).
        # UNAME=Linux selects upstream's own Linux branch — see module docstring.
        self.run(
            f"make -j1 UNAME=Linux CC={shlex.quote(cc)} "
            f"CFLAGS={shlex.quote(cflags)} LDFLAGS={shlex.quote(ldflags)}",
            cwd=self.source_folder,
        )

    def package(self):
        binary = os.path.join(self.source_folder, "xcwd")
        if not os.path.isfile(binary):
            raise ConanException(
                f"upstream build did not produce the expected binary: {binary}")
        copy(self, "xcwd", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Application package: the deliverable is the CLI executable (R38).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

    # ── helpers ──────────────────────────────────────────────────────────────
    def _dependency_flags(self):
        """-I / -L flags for the Conan-provided X11 headers and libraries."""
        includes, lib_dirs = [], []
        for name in DEPENDENCY_FLAG_SOURCES:
            dependency = self.dependencies[name]
            for include in dependency.cpp_info.includedirs:
                includes.append(f"-I{self._resolve(dependency, include)}")
            for libdir in dependency.cpp_info.libdirs:
                lib_dirs.append(f"-L{self._resolve(dependency, libdir)}")
        return includes, lib_dirs

    @staticmethod
    def _resolve(dependency, path):
        """cpp_info dirs may be absolute or package-relative."""
        if os.path.isabs(path):
            return path
        return os.path.join(dependency.package_folder, path)
