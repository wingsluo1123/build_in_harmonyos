#!/usr/bin/env python3
"""Conan recipe for cdparanoia 10.2 on HarmonyOS PC.

cdparanoia is a CDDA reading library for extracting digital audio
from CD-ROM drives. It provides libcdda_interface and libcdda_paranoia
static libraries.

OHOS-specific adaptations:
  - configure.guess/sub patched for OHOS platform detection
  - Bypass autoconf 2.59 configure (has bugs with pre-set CC on OHOS)
  - Build directly from Makefile.in with explicit variables
  - Static libraries only (no shared lib for system safety)
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CdparanoiaConan(ConanFile):
    name = "cdparanoia"
    version = "10.2"
    description = "CDDA reading library for extracting digital audio from CDs"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.xiph.org/paranoia/"

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder
        prefix = self.package_folder

        # Bypass autoconf 2.59 configure (has OBJEXT bugs with pre-set CC)
        # Build directly using Makefile.in with explicit variable substitution
        cc = "/data/service/hnp/bin/clang"
        ar = "/data/service/hnp/bin/llvm-ar"
        ranlib = "/data/service/hnp/bin/llvm-ranlib"
        cflags = ["-fPIC", "-O2", "-fsigned-char", "-Wno-error=int-conversion", "-Wno-error=implicit-function-declaration"]

        # Build interface library (libcdda_interface.a)
        iface_dir = os.path.join(src, "interface")
        iface_srcs = ["cdda_interface.c", "cdda_caps_unix.c", "cdda_generic_unix.c",
                       "cdda_low_interface.c", "common_interface.c", "scan_devices.c",
                       "smallvector.c", "test_interface.c", "utils.c"]

        for s in iface_srcs:
            spath = os.path.join(iface_dir, s)
            if os.path.exists(spath):
                subprocess.run([cc, "-c"] + cflags + ["-I", iface_dir, "-o",
                               os.path.join(iface_dir, s.replace(".c", ".o")), spath],
                              check=True, cwd=iface_dir)

        # Create libcdda_interface.a
        iface_objs = [os.path.join(iface_dir, s.replace(".c", ".o")) for s in iface_srcs
                       if os.path.exists(os.path.join(iface_dir, s))]
        subprocess.run([ar, "rcs", os.path.join(iface_dir, "libcdda_interface.a")] + iface_objs, check=True)
        subprocess.run([ranlib, os.path.join(iface_dir, "libcdda_interface.a")], check=True)

        # Build paranoia library (libcdda_paranoia.a)
        paranoia_dir = os.path.join(src, "paranoia")
        paranoia_srcs = ["cdda_paranoia.c", "gap.c", "isort.c", "overlap.c", "p_block.c"]

        for s in paranoia_srcs:
            spath = os.path.join(paranoia_dir, s)
            if os.path.exists(spath):
                subprocess.run([cc, "-c"] + cflags + ["-I", iface_dir, "-I", paranoia_dir, "-o",
                               os.path.join(paranoia_dir, s.replace(".c", ".o")), spath],
                              check=True, cwd=paranoia_dir)

        paranoia_objs = [os.path.join(paranoia_dir, s.replace(".c", ".o")) for s in paranoia_srcs
                          if os.path.exists(os.path.join(paranoia_dir, s))]
        subprocess.run([ar, "rcs", os.path.join(paranoia_dir, "libcdda_paranoia.a")] + paranoia_objs, check=True)
        subprocess.run([ranlib, os.path.join(paranoia_dir, "libcdda_paranoia.a")], check=True)

    def package(self):
        prefix = self.package_folder
        os.makedirs(f"{prefix}/lib", exist_ok=True)
        os.makedirs(f"{prefix}/include/cdda", exist_ok=True)

        src = self.source_folder
        # Copy static libraries
        for lib in ["libcdda_interface.a", "libcdda_paranoia.a"]:
            for subdir in ["interface", "paranoia"]:
                srcpath = os.path.join(src, subdir, lib)
                if os.path.exists(srcpath):
                    shutil.copy2(srcpath, f"{prefix}/lib/")
                    break

        # Copy headers
        for hdr in ["cdda_interface.h", "cdda_paranoia.h", "utils.h"]:
            for subdir in ["interface", "paranoia", "."]:
                srcpath = os.path.join(src, subdir, hdr)
                if os.path.exists(srcpath):
                    shutil.copy2(srcpath, f"{prefix}/include/cdda/")
                    break

    def package_info(self):
        self.cpp_info.libs = ["cdda_paranoia", "cdda_interface"]
        self.cpp_info.includedirs = ["include/cdda"]
