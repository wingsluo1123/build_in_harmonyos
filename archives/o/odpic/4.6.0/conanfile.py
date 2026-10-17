#!/usr/bin/env python3
"""Conan recipe -- odpic 4.6.0 (Oracle Database Programming Interface for C).

Upstream project: oracle/odpi tag v4.6.0.  The tarball's include/dpi.h carries
DPI_MAJOR_VERSION=4 / DPI_MINOR_VERSION=6 / DPI_PATCH_LEVEL=0, so the build
produces lib/libodpic.so.4.6.0 with SONAME libodpic.so.4 -- hence the package
name "odpic" (the upstream library product name).  It is not the same recipe as
the already archived sibling archive "odpi/6.0.0" (same upstream project, newer
upstream version), which is why this one is registered under its own name and
version directory.

Pure Makefile project: there is no ./configure, no autotools, no cmake/meson.

OHOS porting notes
------------------
1. The upstream Makefile hard-codes the toolchain with plain assignments
   ("CC = gcc" / "LD = gcc", not "?="), while the OHOS host only ships clang.
   Both variables must therefore be overridden on the make command line with
   values taken from the Conan conf (R33: never rely on bare ${CC} / ${CFLAGS}).
2. The same overrides are mandatory for "make install": Makefile:114 lists the
   lib/ *directory* as a normal (non order-only) prerequisite of
   lib/libodpic.so.4.6.0, and the "all" target's two `ln -sf` calls bump lib/'s
   mtime *after* the link.  Any later make invocation therefore re-runs the link
   rule; without the override that re-link falls back to gcc and dies with
   "make: gcc: No such file or directory" (exit 127).
3. "uname -s" on the OHOS host reports "HarmonyOS", so the Makefile's Darwin
   branch is never taken and the ELF branch with -Wl,-soname,libodpic.so.4 is
   used as intended.
4. Upstream links -ldl -lpthread.  On the OHOS musl runtime both are provided by
   libc.so, so the packaged library records DT_NEEDED = libc.so only.
5. OCI (libclntsh) is dlopen()ed at run time and is never linked at build time,
   so this recipe has no build requirements at all (R36 clean).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class OdpicConan(ConanFile):
    name = "odpic"
    version = "4.6.0"
    description = ("Oracle Database Programming Interface for C (ODPI-C) -- "
                   "C library that provides a common API over the Oracle Client "
                   "libraries for accessing Oracle Database")
    license = "UPL-1.0 OR Apache-2.0"
    homepage = "https://github.com/oracle/odpi"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("oracle", "database", "odpic", "odpi", "dpi", "oci", "c-library")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: the compiler comes from the Conan conf, never from bare shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or "clang"

        # Makefile:45-46 assign CC/LD to gcc unconditionally.  LD is used as the
        # link *driver* (it carries -shared and -Wl,-soname), so it has to be the
        # same clang driver, not binutils ld.  R9: always -j1.
        self.run(f'make CC="{cc}" LD="{cc}" -j1', cwd=self.source_folder)

    def package(self):
        copy(self, "dpi.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        # copy() preserves symlinks, so the upstream chain
        # libodpic.so -> libodpic.so.4 -> libodpic.so.4.6.0 is rebuilt verbatim.
        copy(self, "libodpic.so*",
             src=os.path.join(self.source_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "NOTICE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["odpic"]
        self.cpp_info.set_property("cmake_file_name", "dpi")
        self.cpp_info.set_property("cmake_target_name", "dpi::odpic")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "pthread"]
