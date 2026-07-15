#!/usr/bin/env python3
"""Conan recipe for scsi-tgt v1.0 — SCSI target framework (Makefile project).

scsi-tgt (tgt) is a SCSI target framework for Linux/OpenHarmony.
It provides tgtd (daemon), tgtadm (admin tool), and tgtimg (image tool).
Build system: plain Makefile (no configure script needed).
Output: usr/tgtd, usr/tgtadm, usr/tgtimg (command-line tools, not libraries).

Platform compatibility:
  - pthread_cancel replaced with stop-flag pattern (musl compatibility)
  - strict-prototypes warnings fixed for -Werror
  - doc/Makefile patched for xsltproc absence
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ScsiTgtConan(ConanFile):
    name = "scsi-tgt"
    version = "v1.0"
    description = "SCSI target daemon and administration tool"
    license = "GPL-2.0"
    homepage = "https://github.com/fujita/tgt"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies (pure C, only libc + pthread + dl)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R9: Always use -j1 for reliability on memory-constrained systems
        # The top-level Makefile delegates to usr/Makefile, doc/, conf/, scripts/
        # CC is picked up from environment (set by Conan profile / PATH)
        # Use -C to ensure make runs in the source directory (basic_layout uses build-release subdir)
        self.run(f"make -C {self.source_folder} -j1")

    def package(self):
        # Copy compiled binaries from usr/ to bin/ in package folder
        src_usr = os.path.join(self.source_folder, "usr")
        copy(self, "tgtd", src=src_usr, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "tgtadm", src=src_usr, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "tgtimg", src=src_usr, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # scsi-tgt is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
