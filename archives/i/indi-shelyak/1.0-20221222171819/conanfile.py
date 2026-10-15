#!/usr/bin/env python3
"""Conan recipe for indi-shelyak 1.0-20221222171819 — Shelyak eShel / SPOX
spectrograph INDI drivers, shipped as a subproject of the INDI 3rdparty monorepo.

Source strategy (libfishcamp precedent):
  * Upstream lives inside the indi-3rdparty monorepo as the indi-shelyak/
    subdirectory. Pulling the whole monorepo tarball is infeasible (repo ~3.3GB),
    so the 9 driver source files plus the 4 cmake_modules files actually used by
    find_package(INDI) are fetched directly from the official GitHub tag v2.2.5
    (raw.githubusercontent.com is GitHub's official raw host — PF7 compliant).
  * Only files referenced by the build are vendored; no mirrors, no forks.

Build notes (CMake):
  * find_package(INDI REQUIRED) resolves via the vendored FindINDI.cmake with
    INDI_ROOT pointed at the libindi conan package (same pattern as
    libfli/2.0-20221221182632).
  * CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF so the vendored Find*.cmake modules win
    over Conan's CMakeDeps CONFIG lookups (same block as libindi/libfli).
  * CMAKE_SYSTEM_NAME=Linux (E092): CMake has no HarmonyOS platform entry.
  * INDI_DATA_DIR is pinned to share/indi so indi_shelyak.xml installs into the
    package's own prefix instead of libindi's absolute share/indi path.
  * The shelyak CMakeLists.txt also probes `../cmake_modules/`; the vendored
    cmake_modules/ directory at the source root satisfies the first CMAKE_MODULE_PATH
    entry (${CMAKE_CURRENT_SOURCE_DIR}/cmake_modules/), which resolves first.
"""
import os
import textwrap

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.files import apply_conandata_patches, download, export_conandata_patches


class PreferConfigOffBlock(Block):
    """Force CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF so the vendored FindINDI.cmake
    module wins over CMakeDeps CONFIG lookups (same as libindi/libfli)."""
    template = textwrap.dedent("""\
        set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)
    """)


class IndishelyakConan(ConanFile):
    name = "indi-shelyak"
    version = "1.0-20221222171819"
    description = "Shelyak eShel / SPOX spectrograph INDI drivers (INDI 3rdparty)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/indilib/indi-3rdparty"
    url = "https://github.com/indilib/indi-3rdparty"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0 preflight verified: libindi/2.2.2.1 published on ohpcd. The drivers
        # link ${INDI_DRIVER_LIBRARIES} (libindidriver, libindiAlignmentDriver)
        # and include indidevapi.h/indicom.h from the libindi package.
        self.requires("libindi/2.2.2.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Individual official source files (raw.githubusercontent.com, official
        # GitHub raw host). download() rather than get() — plain files, no
        # archives. Filenames keep their subdirectory so the vendored
        # cmake_modules/ tree is reconstructed for find_package(INDI).
        for src in self.conan_data["sources"]:
            download(self, src["url"], src["filename"], sha256=src["sha256"])

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake has no HarmonyOS platform; drive the Linux path.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Point FindINDI.cmake at the libindi conan package (headers + libs).
        tc.variables["INDI_ROOT"] = self.dependencies["libindi"].package_folder
        # INDI_DATA_DIR defaults to libindi's absolute share/indi path (where
        # drivers.xml lives); pin it to the package's own prefix so
        # indi_shelyak.xml installs into package/share/indi (never into the
        # dependency's folder).
        tc.variables["INDI_DATA_DIR"] = "share/indi"
        # Make the vendored FindINDI.cmake module win over CONFIG lookups.
        tc.blocks["prefer_config_off"] = PreferConfigOffBlock
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # INDI_DATA_DIR is also passed as a command-line -D cache variable so it
        # survives find_path(INDI_DATA_DIR ...) inside FindINDI.cmake (a toolchain
        # normal variable would be re-detected to libindi's absolute share/indi;
        # a -D cache entry wins). Same rationale as libfli's
        # CMAKE_POLICY_VERSION_MINIMUM -D. Keeps indi_shelyak.xml installing into
        # this package's share/indi instead of the dependency's folder.
        cmake.configure(cli_args=["-DINDI_DATA_DIR=share/indi"])
        # R9: conservative parallelism; tools.build:jobs can raise it.
        jobs = self.conf.get("tools.build:jobs", default=2)
        cmake.build(cli_args=[f"-j{jobs}"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Command-line drivers only — no library for consumers to link.
        self.cpp_info.bindirs = ["bin"]
