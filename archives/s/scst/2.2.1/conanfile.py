#!/usr/bin/env python3
"""Conan recipe — scst 2.2.1 (SCST core headers, userspace-consumable subset).

SCST (SCSI target subsystem, https://sourceforge.net/projects/scst/) is a
Linux-kernel SCSI target framework: its core product is a set of kernel
modules that can never be built outside a Linux kernel build tree.

This package therefore delivers the *userspace-consumable subset* of the
core include/ tree:

  - scst_const.h  : shared protocol constants / version macros. Proven to
                    compile in userspace on OHOS (linux/version.h and
                    scsi/scsi.h both exist in the OHOS sysroot); it is the
                    only scst core header required by the iscsi-scst 2.2.1
                    userland daemon (usr/event.c).
  - scst_user.h   : user-mode interface definitions for the scst_user
                    passthrough module; userspace branch includes
                    <scst_const.h> only (#ifdef INSIDE_KERNEL_TREE guarded).

Deliberately excluded (kernel-tree-only, include linux/blkdev.h,
linux/autoconf.h, scsi/scsi_cmnd.h ... — unusable outside a kernel build):
scst.h, scst_debug.h, scst_sgv.h. See notes.md for the full boundary
declaration.

R32 note: no settings.os branch is needed — the headers are platform
neutral; the only requirement is a sysroot that ships linux/version.h and
scsi/scsi.h (true for the OHOS SDK sysroot).
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ScstConan(ConanFile):
    name = "scst"
    version = "2.2.1"
    description = (
        "SCST (SCSI target subsystem) core headers — userspace-consumable "
        "subset (scst_const.h, scst_user.h) of the SCST 2.2.1 include/ tree"
    )
    license = "GPL-2.0-only"
    homepage = "https://sourceforge.net/projects/scst/"
    url = "https://sourceforge.net/projects/scst/"
    topics = ("scsi", "target", "storage", "headers", "kernel")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # header-only, no dependencies
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only: nothing to compile; house pattern G1 (no-op when patches: {})
        apply_conandata_patches(self)

    def package(self):
        src_inc = os.path.join(self.source_folder, "include")
        # Userspace-consumable subset only (see module docstring / notes.md)
        copy(self, "scst_const.h", src_inc,
             os.path.join(self.package_folder, "include"))
        copy(self, "scst_user.h", src_inc,
             os.path.join(self.package_folder, "include"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "scst")
        self.cpp_info.set_property("cmake_target_name", "scst::scst")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
