#!/usr/bin/env python3
"""Conan recipe for mailx 8.1.2_git20220412 (upstream Makefile build).

mailx 8.1.2_git20220412 is the Alpine name for the BSD mailx snapshot that
Debian ships as bsd-mailx 8.1.2-0.20220412cvs: the traditional command line
mail user agent (send/receive mail). The adaptation mirrors the already
merged bsd-mailx 8.1.2-0.20220412cvs recipe (same upstream sources, same
13 patches, same ported vis(3) implementation); only the installed binary
name is mailx instead of bsd-mailx.

The upstream source uses OpenBSD bsd.prog.mk; our adaptation replaces it
with a GNU-make compatible Makefile (see patches/). No external runtime
dependencies: the OpenBSD-specific pledge(2)/vis(3) pieces are handled in
the source adaptation without liblockfile/libbsd.

vis.c/vis.h are new source files (not present upstream) providing the BSD
vis(3) API that OHOS libc lacks; they are shipped via exports_sources and
copied into the source tree during build (not via patches/ so that
refresh-patch does not regenerate them as new-file patches).
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class MailxConan(ConanFile):
    name = "mailx"
    version = "8.1.2_git20220412"
    description = "BSD mailx: the traditional command line mail user agent (send/receive mail)."
    license = "BSD-3-Clause"
    homepage = "https://salsa.debian.org/debian/bsd-mailx"
    url = "https://salsa.debian.org/debian/bsd-mailx"
    topics = ("mail", "mailx", "mua", "bsd")
    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)
        # vis.c/vis.h are OHOS-specific additions (BSD vis(3) API not in
        # OHOS libc). Ship them with the recipe and copy into the source
        # tree at build time.
        copy(self, "vis.c", src=self.recipe_folder, dst=self.export_sources_folder)
        copy(self, "vis.h", src=self.recipe_folder, dst=self.export_sources_folder)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mailx requires a POSIX host (Linux or OHOS)")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Copy the OHOS-specific vis(3) implementation into the source tree.
        copy(self, "vis.c", src=self.export_sources_folder, dst=self.source_folder)
        copy(self, "vis.h", src=self.export_sources_folder, dst=self.source_folder)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = (compilers.get("c") or "clang").strip()
        # The profile hard-codes the CI worker layout
        # (/data/service/hnp/bin/clang); on machines where that absolute
        # path does not exist, fall back to resolving the compiler from
        # PATH (the profile/preflight also prepends the real toolchain
        # bin/ to PATH). Keeps CI semantics when the path exists.
        if not os.path.isfile(cc):
            resolved = (
                shutil.which(os.path.basename(cc))
                or shutil.which("clang")
                or shutil.which("cc")
                or cc
            )
            if resolved != cc:
                self.output.warning(
                    "configured C compiler '{}' not found, "
                    "falling back to PATH lookup: {}".format(cc, resolved)
                )
            cc = resolved
        self.output.info("Using C compiler: {}".format(cc))
        self.run('make -j1 CC="{}"'.format(cc))

    def package(self):
        self.run(
            "make install DESTDIR={}".format(self.package_folder)
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
