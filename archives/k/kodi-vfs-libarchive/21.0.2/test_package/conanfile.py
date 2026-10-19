#!/usr/bin/env python3
"""Conan test_package for kodi-vfs-libarchive 21.0.2 — consumer-side check.

The add-on is a Kodi-host-loaded module without a standalone entry point, so
the test loads the packaged module with dlopen() and verifies the Kodi 21
binary add-on entry points (ADDON_Create, ADDON_GetTypeVersion,
ADDON_GetTypeMinVersion), the VFS instance API version reported through
ADDON_GetTypeVersion() against kodi/versions.h of the xbmc 21.3-Omega SDK,
and that the module's explicit libarchive DT_NEEDED closure actually loads
and serves the libarchive public API on the musl-based OHOS target.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class KodiVfsLibarchiveTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # Location of the packaged module, passed to the test binary/command.
        toolchain.variables["ADDON_LIB_DIR"] = \
            self.dependencies["kodi-vfs-libarchive"].cpp_info.libdirs[0]
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built VFS add-on consumer cannot run on this host")
            return
        addon_so = os.path.join(
            self.dependencies["kodi-vfs-libarchive"].cpp_info.libdirs[0],
            "vfs.libarchive.so")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_vfs_libarchive")
        # The module is dlopen()ed, so its own DT_NEEDED shared dependencies
        # (conan-provided libarchive, and libarchive's dynamic zstd) must be
        # resolvable by the loader at dlopen time — prepend their package lib
        # dirs explicitly instead of relying on the run environment's default
        # collection.
        dep_libdirs = [self.dependencies[dep].cpp_info.libdirs[0]
                       for dep in ("libarchive", "zstd")]
        env_prefix = "LD_LIBRARY_PATH=%s" % ":".join(dep_libdirs + ["$LD_LIBRARY_PATH"])
        self.run("%s %s %s" % (env_prefix, test_bin, addon_so), env="conanrun")
