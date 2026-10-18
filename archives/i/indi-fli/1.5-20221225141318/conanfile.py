#!/usr/bin/env python3
"""Conan recipe for indi-fli 1.5-20221225141318 — INDI driver package for
Finger Lakes Instrument (FLI) hardware, shipped as a subproject of the INDI
3rdparty tree (snapshot published by the Debian Astronomy Team, see
conandata.yml).

The package product is the FLI driver family:

  * bin/indi_fli_ccd      — CCD camera driver   (INDI::CCD)
  * bin/indi_fli_wheel    — filter wheel driver (INDI::FilterWheel)
  * bin/indi_fli_focus    — focuser driver      (INDI::Focuser)
  * share/indi/indi_fli.xml — INDI driver descriptor for the CCD driver

The optional Kepler/FLIPRO branch (bin/indi_kepler_ccd) is *not* enabled: it
requires the proprietary FLIPRO SDK (find_package(FLIPRO), non-free, not in the
OHOS registry), and the upstream CMakeLists.txt already treats it as optional.

Adaptation points for OHOS (full record in notes.md):
  * E092 — CMake has no HarmonyOS platform, so CMAKE_SYSTEM_NAME is forced to
    Linux and CMAKE_SYSTEM_PROCESSOR is pinned to aarch64 (same workaround as
    libindi/2.2.2.1, libfli/2.0-20221221182632 and the sibling drivers
    indi-fishcamp / indi-gpsnmea / indi-beefocus in this repository).
  * CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF — the 2022-era cmake_modules/
    FindINDI.cmake / FindFLI.cmake / FindCFITSIO.cmake shipped in the driver
    tree must win over the CONFIG packages CMakeToolchain would look for.
  * INDI_ROOT — points the vendored FindINDI.cmake at the pre-built libindi
    package instead of a system installation.
  * Patch 0001 backports the upstream FindINDI version regex: INDI >= 2.0
    writes `#define INDI_VERSION "2.2.2"` (with quotes), which the 2022 regex
    cannot match ("failed to detect INDI version").
  * Patch 0002 raises the vendor CMakeCommon.cmake standard from C++14 to
    C++17 (INDI 2.x headers use std::any); identical to upstream master.
  * Patch 0003 fixes three genuine build defects of the snapshot:
    cmake_minimum_required(3.0) is rejected by CMake >= 4, the driver links the
    *static* libfli.a whose USB backend needs libusb-1.0 on the link line, and
    INDI_DATA_DIR has to be redirected so the driver XML does not get installed
    into the libindi package.
  * Patch 0004 ports the three driver sources from the INDI 1.x property API to
    the INDI 2.x one (base class members became INDI::Property* objects).

Upstream tests: none.  The driver tree ships no test case and the CMakeLists
has no enable_testing()/add_test(); the packaged artefacts are verified by
test_package/check_driver.py (ELF/XML/linkage closure + best-effort exec).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class PreferConfigOffBlock(Block):
    """Force CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF so the Find*.cmake modules
    vendored in the driver tree win over the CONFIG package lookups that
    CMakeToolchain enables by default.  The block runs last, overriding the
    toolchain default."""
    template = "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)\n"


class IndifliConan(ConanFile):
    name = "indi-fli"
    version = "1.5-20221225141318"
    description = ("INDI driver package for Finger Lakes Instrument (FLI) CCDs, "
                   "filter wheels and focusers (INDI 3rdparty)")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/indilib/indi-3rdparty"
    url = "https://github.com/indilib/indi-3rdparty"
    topics = ("astronomy", "indi", "ccd", "filter-wheel", "focuser", "driver")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Matches the upstream CMakeLists.txt: find_package(INDI REQUIRED),
        # find_package(FLI REQUIRED), find_package(CFITSIO REQUIRED),
        # find_package(ZLIB REQUIRED).  libusb is the runtime dependency of the
        # *static* libfli.a that this driver links (patch 0003 adds it to the
        # link line); all six packages are published in the OHOS registry.
        self.requires("libindi/2.2.2.1")
        self.requires("libfli/2.0-20221221182632")
        self.requires("cfitsio/4.6.4")
        self.requires("zlib/1.3.1.1")
        self.requires("libusb/1.0.27")

    # R32: only Linux-family targets are supported.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"indi-fli is only supported on Linux/OHOS, not {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake has no HarmonyOS platform; drive the Linux path instead.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Let the vendored FindINDI.cmake resolve the pre-built libindi package
        # (it searches INDI_ROOT before any system prefix).
        tc.variables["INDI_ROOT"] = self.dependencies["libindi"].package_folder
        # Make the vendored Find*.cmake modules win over CONFIG lookups.
        tc.blocks["prefer_config_off"] = PreferConfigOffBlock
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # The snapshot declares cmake_minimum_required(VERSION 3.0); CMake >= 4
        # dropped compatibility below 3.5.  Patch 0003 already raises the
        # declaration, and this cache entry keeps the build working even if a
        # future upstream refresh brings 3.0 back.
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        # R9: conservative parallelism; tools.build:jobs can raise it.
        jobs = self.conf.get("tools.build:jobs", default=2)
        cmake.build(cli_args=[f"-j{jobs}"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream ships no LICENSE file; the driver sources carry the LGPL-2.1+
        # header (see notes.md "许可").

    def package_info(self):
        # Application package: the deliverable is the driver executables plus
        # the INDI device descriptor.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        # libindi is published static-first, so Conan does not put its lib
        # directory into the run environment, while the drivers link libindi's
        # shared objects (libindidriver.so / libindiclient.so / libindilx200.so).
        # Declare the run-time search path so test_package and downstream
        # consumers can actually load the driver (same handling as indi-aok).
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH",
            self.dependencies["libindi"].cpp_info.libdirs[0])
