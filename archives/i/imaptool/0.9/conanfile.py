#!/usr/bin/env python3
"""Conan recipe — imaptool 0.9

imaptool is a small X11/Athena-widget application (Seth Spitzer, 2000) that
turns a JPEG or GIF picture into an HTML client-side image map: it draws the
picture in a window and lets the user mark rectangle / circle / polygon
regions, then dumps the matching ``<area>`` HTML.

Build system: a hand-written GNU Makefile (no configure script, no upstream
test suite).  The Makefile hard-codes ``CC=gcc -I/usr/X11R6/include/``,
``JPEG_INCLUDE=-I/usr/local/include/`` and
``LIBDIR=-L/usr/local/lib -L/usr/X11R6/lib``; the recipe overrides those
variables on the ``make`` command line with the real Conan dependency
directories (no Makefile patch needed — the same technique as
archives/c/coolmail/1.3).

The bundled GIF decoder (dgif_lib.c / gif_err.c / gifalloc.c) is compiled from
the upstream sources; there is no external giflib dependency.

OHOS notes: the package is a command-line GUI binary; the device and the CI
worker have no X server (no Xorg/Xvfb in the image), so the consumer test
exercises the no-display code path and the ELF metadata (see
test_package/test_imaptool.py).  The packaged executable is self-signed for
OHOS in package().
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rename,
)
from conan.tools.layout import basic_layout


class ImaptoolConan(ConanFile):
    name = "imaptool"
    version = "0.9"
    description = ("X11 image-map authoring tool — draws clickable rectangle / "
                   "circle / polygon regions over a JPEG or GIF picture and "
                   "emits the matching HTML <area> map")
    license = "GPL-2.0-or-later"
    homepage = "http://www.sspitzer.org/imaptool/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Athena-widget application: libXaw widgets on top of the X Toolkit
        # Intrinsics (XtVaAppInitialize / XtCreateManagedWidget in imaptool.c)
        # and Xlib.  Versions are the published ohpcd X11 stack
        # (`conan list -r=ohpcd`), the same graph archives/x/xfontsel/1.1.2
        # builds against.
        self.requires(
            "libx11/1.8.13", force=True, transitive_headers=True, transitive_libs=True
        )
        self.requires("libxext/6.4.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxt/1.3.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxmu/1.3.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxaw/1.0.14", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)
        # file2pixmap.c compiles the JPEG loader under -DUSE_JPEG_LIB
        # (<jpeglib.h> / <jerror.h>); libjpeg/10 is published static.
        self.requires("libjpeg/10", transitive_headers=True, transitive_libs=True)
        # Runtime closure of the linked X11 libraries (libXaw7/libXt/libXmu
        # DT_NEEDED pull libX11 → libxcb → libXau/libXdmcp).  run=True only
        # injects their libdirs into the test_package conanrun environment.
        self.requires("libxcb/1.17.0", run=True)
        self.requires("libxau/1.0.11", run=True)
        self.requires("libxdmcp/1.1.5", run=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"imaptool supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # X11 / jpeg dependency paths
    # ------------------------------------------------------------------
    def _dependency_dirs(self, kind):
        """Absolute include/lib directories of every host dependency."""
        attr = "includedirs" if kind == "include" else "libdirs"
        found, seen = [], set()
        for _, dep in self.dependencies.host.items():
            base = dep.package_folder or ""
            for entry in getattr(dep.cpp_info, attr):
                path = entry if os.path.isabs(entry) else os.path.join(base, entry)
                if os.path.isdir(path) and path not in seen:
                    seen.add(path)
                    found.append(path)
        return found

    def generate(self):
        self._inc_dirs = self._dependency_dirs("include")
        self._lib_dirs = self._dependency_dirs("lib")

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler comes from the Conan conf / profile, never from the
        # shell environment.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"
        cflags = "-O2" if self.settings.build_type == "Release" else "-O0 -g"

        includes = " ".join(f"-I{d}" for d in self._inc_dirs)
        libdirs = " ".join(f"-L{d}" for d in self._lib_dirs)

        # Override the Makefile's hard-coded X11R6/usr-local paths on the make
        # command line:
        #   CC          — replaces "gcc -I/usr/X11R6/include/" (compile + link)
        #   JPEG_INCLUDE — replaces "-I/usr/local/include/" (expanded inside
        #                  JPEG_CHOICE for the file2pixmap.o rule)
        #   LIBDIR      — replaces "-L/usr/local/lib -L/usr/X11R6/lib"
        # LIBRARIES (-lXt -lXaw -lXmu -lXext -lX11 -ljpeg -lm) is left as
        # upstream wrote it; every one of those libs is supplied by the
        # declared Conan dependencies.
        command = (
            f'make -j1 CC="{cc} {cflags} {includes}" '
            f'JPEG_INCLUDE="{includes}" '
            f'LIBDIR="{libdirs}"'
        )
        self.output.info(f"imaptool build command: {command}")
        self.run(command, cwd=self.source_folder)

    # ------------------------------------------------------------------
    # OHOS ELF signing (OHOS refuses to execute an unsigned ELF)
    # ------------------------------------------------------------------
    @staticmethod
    def _sign_ohos_elf(path):
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = (
            shutil.which("llvm-readelf")
            or "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(path):
            raise ConanException(f"missing packaged executable: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException(
                "OHOS signing tools missing (binary-sign-tool / llvm-readelf)"
            )
        original_mode = os.stat(path).st_mode & 0o777
        signed = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
            check=True,
            timeout=120,
        )
        sections = subprocess.run(
            [readelf, "-SW", signed],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout
        count = sections.count(".codesign")
        if count != 1:
            raise ConanException(
                f"signed ELF must have exactly one .codesign section, found {count}"
            )
        mode = original_mode if original_mode & 0o111 else original_mode | 0o755
        os.replace(signed, path)
        os.chmod(path, mode)

    def package(self):
        binary = os.path.join(self.package_folder, "bin", "imaptool")
        copy(self, "imaptool", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        if str(self.settings.os) == "OHOS" and os.path.isfile(binary):
            self._sign_ohos_elf(binary)

        copy(self, "LICENCE.TXT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        copy(self, "imaptool.man", src=self.source_folder, dst=man_dir)
        rename(self, os.path.join(man_dir, "imaptool.man"),
               os.path.join(man_dir, "imaptool.1"))

    def package_info(self):
        # Command-line application: no headers and no libraries (R38).
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
