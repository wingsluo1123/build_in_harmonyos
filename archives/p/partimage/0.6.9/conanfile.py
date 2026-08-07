#!/usr/bin/env python3
"""Conan recipe for partimage 0.6.9 — Partition Image backup/restore tool.

partimage is a command-line tool for backing up disk partitions into
compressed image files. It supports gzip/bzip2 compression and
network-based image storage via partimaged server.

On HarmonyOS, newt GUI and SSL are disabled (--disable-newt --disable-ssl);
the tool runs in batch/non-interactive mode.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout

import os


class PartimageConan(ConanFile):
    name = "partimage"
    version = "0.6.9"
    description = "Partition Image backup/restore tool for Linux disk partitions"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/partimage/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # The 'compile' automake auxiliary script and 'gui_text.h' (rewritten for
        # HAVE_LIBNEWT dummy classes) are missing from / can't be patched in the tarball.
        # Conan 2.x can't create new files via patches, so we export them as
        # standalone files and copy them in build().
        copy(self, "compile", src=self.recipe_folder, dst=self.export_sources_folder)
        copy(self, "gui_text.h", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("bzip2/1.0.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-newt")
        tc.configure_args.append("--disable-ssl")
        # gettext/libintl is a system library from the gettext HNP package
        tc.configure_args.append("--with-libintl-prefix=/data/service/hnp/gettext.org/gettext_0.26")
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        # Copy missing/rewritten files before patching and configure
        copy(self, "compile", src=self.export_sources_folder, dst=self.source_folder)
        copy(self, "gui_text.h", src=self.export_sources_folder, dst=os.path.join(self.source_folder, "src", "client"))
        apply_conandata_patches(self)
        # Touch generated files to prevent make from trying to regenerate them
        # (automake/aclocal not available in the build environment)
        for f in ["aclocal.m4", "config.h.in", "config.status",
                   "configure", "Makefile.in", "src/Makefile.in",
                   "src/client/Makefile.in", "src/client/fs/Makefile.in",
                   "src/server/Makefile.in", "src/shared/Makefile.in",
                   "m4/Makefile.in", "po/Makefile.in.in"]:
            path = os.path.join(self.source_folder, f)
            if os.path.exists(path):
                os.utime(path, None)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["intl"]
