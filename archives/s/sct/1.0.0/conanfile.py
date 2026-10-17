#!/usr/bin/env python3
"""Conan recipe — sct 1.0.0 (X11 screen color temperature tool).

Upstream: https://github.com/0mp/sct (FreeBSD port of Ted Unangst's sct).
Build system: plain Makefile (no configure).
License: Unlicense.

X11/XRandR are taken from the ohpcd registry (libxrandr/1.5.5.1 pulls
libx11/6.4.0, libxrender, libxext, xorgproto); nothing is linked from
pre-installed host paths, so CI workers see the same dependency graph.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class SctConan(ConanFile):
    name = "sct"
    version = "1.0.0"
    description = "Set the screen color temperature on X11 via XRandR"
    license = "Unlicense"
    homepage = "https://github.com/0mp/sct"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libxrandr ships Xrandr.h and pulls libx11 (Xlib.h/Xatom.h/Xproto.h)
        # plus xorgproto (extensions/randr.h) through transitive headers.
        self.requires(
            "libxrandr/1.5.5.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # Export CFLAGS/LDFLAGS through the environment: assigning them on the
        # make command line would override the Makefile's `+=` and drop
        # -lX11/-lXrandr. INCS/LIBS default to /usr/local, so blank them (R33);
        # dependency include paths arrive via CPPFLAGS from AutotoolsDeps.
        self.run(
            f'cd "{self.source_folder}" && '
            'CFLAGS="$CFLAGS $CPPFLAGS -std=c99 -Wall" '
            'LDFLAGS="$LDFLAGS" '
            'make -j1 INCS= LIBS=',
            env="conanbuild",
        )

    def package(self):
        destdir = self.package_folder
        self.run(
            f'cd "{self.source_folder}" && '
            f'make install DESTDIR="{destdir}" PREFIX= MANPREFIX=/share',
            env="conanbuild",
        )

    def package_info(self):
        # Command line tool: only bin/ and the man page are packaged (R38).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
