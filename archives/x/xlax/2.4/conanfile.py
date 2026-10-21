#!/usr/bin/env python3
"""Conan recipe for xlax 2.4 — X11 input multiplexer (HarmonyOS PC / aarch64).

xlax sends the keyboard input typed in its window to a group of other X11
windows at the same time (an "input multiplexer" for XTerm windows).  It is a
single C file written against Xt + the Athena widget set.

Build system
------------
Upstream is a 1992-era Imake project: ``Imakefile`` declares
``ComplexProgramTarget(xlax)`` and the README tells the user to run ``xmkmf``.
There is no imake/xmkmf on HarmonyOS (same situation as xpaint 2.9.1.4, E546),
so the recipe bypasses Imake completely and compiles the single translation
unit with the Conan toolchain compiler; the link line is the expansion of the
upstream ``XawClientLibs`` macro, ``Xaw Xmu Xt X11``, plus ``-lm`` for the
``<math.h>`` helpers the program includes.

The X11 chain comes from the artifact repository, never from the build host:

    libxaw/1.0.14 -> libxt/1.3.1, libxmu/1.3.1.1, libxext/6.4.0.1,
                     libx11/1.8.13, libxpm/3.5.17, xorgproto/2025.1

libxaw 1.0.14 pins libx11/1.8.13 (force) and libxext/6.4.0.1, i.e. the
libx11 track that libxt/libxmu are built against in this repository; the same
chain is spelled out explicitly here so that the recipe documents its ABI
track (this is the xpaint 2.9.1.4 arrangement).

Debian patches
--------------
The two code patches of the Debian packaging (fix-warnings, protos) are
applied; ``use-libbsd.diff`` is not, because OHOS libc provides strlcpy()
itself (see conandata.yml and notes.md).

HarmonyOS adaptation
--------------------
* Imake -> direct compile with the Conan toolchain (E546: no xmkmf).
* ``patches/0003-headless-selftest.patch`` adds a ``--version`` /
  ``--selftest`` path that runs before ``XtAppInitialize()``: HarmonyOS PC has
  no X server, so the GUI can never be created there and the package test must
  exercise the linked Xt/Xaw/Xmu code without a display.
* ``mkxlax`` (a Perl helper that starts and tiles the xterm windows) and its
  man page are installed under ``share/xlax/`` instead of ``bin/``: the OHOS
  base system has no Perl interpreter, and shipping a ``#!/usr/bin/perl``
  script in ``bin/`` would create a command that can only fail with ENOENT.
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
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class XlaxConan(ConanFile):
    name = "xlax"
    version = "2.4"
    description = ("X11 input multiplexer — sends keyboard input to multiple "
                   "X11 windows at once")
    license = "HPND"
    homepage = "https://hea-www.harvard.edu/~fine/Tech/xlax.html"
    url = "https://hea-www.harvard.edu/~fine/Tech/xlax.html"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # X11 chain — the libx11/1.8.13 track that libxt/libxmu/libxaw are
        # built against in this repository (same arrangement as xpaint).
        self.requires("xorgproto/2025.1", transitive_headers=True)
        self.requires("libx11/1.8.13", override=True,
                      transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0.1",
                      transitive_headers=True, transitive_libs=True)
        self.requires("libxt/1.3.1",
                      transitive_headers=True, transitive_libs=True)
        self.requires("libxmu/1.3.1.1",
                      transitive_headers=True, transitive_libs=True)
        self.requires("libxpm/3.5.17",
                      transitive_headers=True, transitive_libs=True)
        self.requires("libxaw/1.0.14",
                      transitive_headers=True, transitive_libs=True)

    def validate(self):
        # R32: settings.os checks must accept both Linux and OHOS.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xlax supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: the compiler and its flags come from the Conan toolchain
        # (conanbuild environment), never from an undefined shell variable.
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        inc_flags = " ".join(f'-I"{d}"' for d in self._dep_dirs("includedirs"))
        lib_flags = " ".join(f'-L"{d}"' for d in self._dep_dirs("libdirs"))

        xlax_src = os.path.join(self.source_folder, "xlax.c")
        xlax_bin = os.path.join(self.build_folder, "xlax")

        # XawClientLibs expands to Xaw Xmu Xt X11; -lXext/-lXpm keep the
        # shared-library link complete (libXaw.so.7 has DT_NEEDED on both).
        self.run(
            f'$CC -std=gnu17 -O2 -Wall -Wno-unused-result {inc_flags} '
            f'"{xlax_src}" -o "{xlax_bin}" '
            f'{lib_flags} -lXaw7 -lXmu -lXt -lX11 -lXext -lXpm -lm',
            env="conanbuild",
        )

    def _dep_dirs(self, attribute):
        """Absolute include/lib directories of the whole host dependency graph.

        Conan 2.29 has no ``self.dependencies.host.aggregated_components()``
        (that helper is newer), so the aggregation is done per dependency with
        a fallback for recipes that define no components.
        """
        seen = []
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            cpp_info = dep.cpp_info
            aggregator = getattr(cpp_info, "aggregated_components", None)
            if aggregator is not None:
                cpp_info = aggregator()
            for directory in getattr(cpp_info, attribute):
                if directory and directory not in seen:
                    seen.append(directory)
        return seen

    def package(self):
        copy(self, "xlax", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        copy(self, "xlax.man", src=self.source_folder, dst=mandir)
        copy(self, "mkxlax.man", src=self.source_folder, dst=mandir)
        for page in ("xlax", "mkxlax"):
            os.rename(os.path.join(mandir, f"{page}.man"),
                      os.path.join(mandir, f"{page}.1"))

        # Perl helper + its sample configuration (no Perl in the OHOS base
        # system, so it is installed as data rather than as a bin/ command).
        copy(self, "mkxlax", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "xlax"))
        copy(self, "dot-mkxlax", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "xlax"))

    def package_info(self):
        # 终端工具，无可链接库；只提供 bin/（R38 → 软件级 commands.json）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
