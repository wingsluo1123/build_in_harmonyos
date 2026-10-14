#!/usr/bin/env python3
"""Conan recipe for sxiv 26.

sxiv is an X11 image viewer.  The published imlib2/1.9.1 package is built
with --without-x, so it intentionally omits the seven display/drawable API
symbols used by sxiv.  This recipe keeps the published imlib2 image pipeline
and supplies the missing drawable operations with a small libX11-backed
compatibility object.  The rest of the adaptation is a plain Makefile build
using the published X11, Xft, fontconfig, giflib and libexif packages.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.layout import basic_layout


class SxivConan(ConanFile):
    name = "sxiv"
    version = "26"
    description = "Simple X image viewer (sxiv) 26"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/muennich/sxiv"
    url = "https://github.com/muennich/sxiv"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = (
        "ohos_x11_render.c",
        "ohos_x11_render.h",
        "ohos_x11_scaling.h",
    )

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "sxiv supports Linux and OHOS only"
            )

    def requirements(self):
        # W0/R36: all direct and transitive requirements below are published
        # in the OHPCD registry.  imlib2 is deliberately consumed as the
        # published --without-x build; the compatibility object below fills
        # only the missing drawable API.
        self.requires("libx11/1.8.13", transitive_headers=True)
        self.requires("libxft/2.3.9", transitive_headers=True)
        self.requires("fontconfig/2.18.3", transitive_headers=True)
        self.requires("imlib2/1.9.1", transitive_headers=True)
        self.requires("giflib/6.1.3")
        self.requires("libexif/0.6.26.1")
        # Keep imlib2's prebuilt ABI while allowing libxft/fontconfig to use
        # the same freetype package in the graph.
        self.requires("freetype/2.14.3.1", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        # exports_sources places these files in source_folder before this
        # method runs, so copying them from export_sources_folder would target
        # the same directory and Conan rejects that operation.
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c")
        if not cc:
            raise ConanInvalidConfiguration(
                "sxiv needs tools.build:compiler_executables.c in the profile"
            )
        return cc

    def _dependency_paths(self, attribute):
        values = []
        for dependency in self.dependencies.host.values():
            cpp_info = dependency.cpp_info
            items = getattr(cpp_info, attribute, None)
            if items:
                values.extend(items)
            for component in getattr(cpp_info, "components", {}).values():
                items = getattr(component, attribute, None)
                if items:
                    values.extend(items)
        unique = []
        for value in values:
            if value not in unique:
                unique.append(value)
        return unique

    def _make_flags(self):
        cc = self._compiler()
        include_flags = " ".join(
            "-I" + path for path in self._dependency_paths("includedirs")
        )
        lib_flags = " ".join(
            "-L" + path for path in self._dependency_paths("libdirs")
        )
        cppflags = (
            "-I. " + include_flags +
            " -include " + os.path.join(self.source_folder, "ohos_x11_render.h") +
            " -D_XOPEN_SOURCE=700 -DHAVE_GIFLIB=1 -DHAVE_LIBEXIF=1"
        )
        ldlibs = (
            lib_flags +
            " -lImlib2 -lX11 -lXft -lfontconfig -lexif -lgif"
        ).strip()
        objects = (
            "autoreload_nop.o commands.o image.o main.o options.o "
            "thumbs.o util.o window.o ohos_x11_render.o"
        )
        return cc, cppflags, ldlibs, objects

    def _make_variables(self):
        cc, cppflags, ldlibs, objects = self._make_flags()
        values = {
            "CC": cc,
            "CFLAGS": "-std=c99 -Wall -pedantic -O2 -DNDEBUG -fPIC",
            "CPPFLAGS": cppflags,
            "LDLIBS": ldlibs,
            "AUTORELOAD": "nop",
            "HAVE_GIFLIB": "1",
            "HAVE_LIBEXIF": "1",
            "objs": objects,
        }
        return " ".join(
            "{}={}".format(key, shlex.quote(value))
            for key, value in values.items()
        )

    def build(self):
        self.run(
            "make {} -j1".format(self._make_variables()),
            cwd=self.source_folder,
        )

    def package(self):
        self.run(
            "make install PREFIX={} MANPREFIX={} {} -j1".format(
                shlex.quote(self.package_folder),
                shlex.quote(os.path.join(self.package_folder, "share", "man")),
                self._make_variables(),
            ),
            cwd=self.source_folder,
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
