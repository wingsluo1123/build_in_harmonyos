#!/usr/bin/env python3
"""Conan recipe for rrsync 3.4.4 — restricted rsync wrapper script (Python).

rrsync is a pure Python3 script shipped in the official rsync source tree
(support/rrsync).  It restricts rsync to a subdirectory declared in
.ssh/authorized_keys.  No compilation is performed (script tool, no-build
family per SKILL v12.21 template variant C).
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RrsyncConan(ConanFile):
    name = "rrsync"
    version = "3.4.4"
    description = "rrsync — script that restricts rsync to a subdirectory declared in .ssh/authorized_keys"
    license = "GPL-3.0-or-later"
    homepage = "https://rsync.samba.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # Runtime requirement: python3 interpreter (provided by the target
    # environment, e.g. the conan python/3.12.9 package or system python3).

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # No compilation: rrsync is an interpreted script (no-build family).
    def build(self):
        pass

    def package(self):
        apply_conandata_patches(self)
        copy(self, "rrsync", os.path.join(self.source_folder, "support"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "rrsync.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
