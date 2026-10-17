#!/usr/bin/env python3
"""Conan recipe for indi-sbig 2.1 — INDI driver package for SBIG / Diffraction
Limited CCD cameras (SN-series host USB driver), shipped as a subproject of the
INDI 3rdparty tree (Debian Astronomy Team snapshot, see conandata.yml).

The package product is bin/indi_sbig_ccd (INDI::CCD) plus its INDI device
descriptor share/indi/indi_sbig.xml, which registers two devices ("SBIG CCD"
and "SBIG ST-I") against the same executable.

Adaptation points for OHOS (full record in notes.md):
  * E092 — CMake has no HarmonyOS platform, so CMAKE_SYSTEM_NAME is forced to
    Linux and CMAKE_SYSTEM_PROCESSOR pinned to aarch64 (same workaround as
    libindi / libsbig / the sibling drivers in this repository).
  * CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF so the vendored cmake_modules/
    FindINDI.cmake / FindSBIG.cmake / FindUSB1.cmake / FindCFITSIO.cmake win.
  * INDI_ROOT points the vendored FindINDI.cmake at the pre-built libindi
    package; the libusb include root is injected because sbig_ccd.h includes
    <libusb-1.0/libusb.h> while the tree's FindUSB1 only reports the leaf dir.
  * Patch 0001 backports the upstream FindINDI version regex (INDI >= 2.0 uses
    `#define INDI_VERSION "2.2.2"` with quotes).
  * Patch 0002 raises the vendor CMakeCommon.cmake standard from C++14 to C++17.
  * Patch 0003 raises cmake_minimum_required to 3.16 (CMake >= 4 rejects 3.0)
    and redirects INDI_DATA_DIR so the descriptor stays in this package.
  * Patch 0004 ports sbig_ccd.cpp from the INDI 1.x property API to 2.x.

Upstream tests: none (no enable_testing()/add_test() in the tree); the packaged
artefacts are verified by test_package/check_driver.py.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class PreferConfigOffBlock(Block):
    """Force CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF so the vendored Find*.cmake
    modules win over CONFIG package lookups."""
    template = "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)\n"


class IndisbigConan(ConanFile):
    name = "indi-sbig"
    version = "2.1"
    description = ("INDI driver package for SBIG (Diffraction Limited) CCD "
                   "cameras, including the filter wheel and AO support")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/indilib/indi-3rdparty"
    url = "https://github.com/indilib/indi-3rdparty"
    topics = ("astronomy", "indi", "ccd", "sbig", "driver")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Matches the upstream CMakeLists.txt: find_package(CFITSIO REQUIRED),
        # find_package(INDI REQUIRED), find_package(ZLIB REQUIRED),
        # find_package(SBIG REQUIRED), find_package(Threads REQUIRED),
        # find_package(USB1 REQUIRED).
        self.requires("libindi/2.2.2.1")
        self.requires("libsbig/4.9.9")
        self.requires("cfitsio/4.6.4")
        self.requires("zlib/1.3.1.1")
        self.requires("libusb/1.0.27")

    # R32: only Linux-family targets are supported.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"indi-sbig is only supported on Linux/OHOS, not {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake has no HarmonyOS platform; drive the Linux path instead.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Let the vendored FindINDI.cmake resolve the pre-built libindi package.
        tc.variables["INDI_ROOT"] = self.dependencies["libindi"].package_folder
        # sbig_ccd.h includes <libusb-1.0/libusb.h> (version-prefixed), while the
        # tree's FindUSB1.cmake only reports the leaf directory and the upstream
        # CMakeLists never adds USB1_INCLUDE_DIRS to the include path — inject the
        # include ROOT (same handling as libfli / indi-sx in this repository).
        usb_inc = self.dependencies["libusb"].cpp_info.includedirs[0]
        if os.path.basename(usb_inc) == "libusb-1.0":
            usb_inc = os.path.dirname(usb_inc)
        tc.extra_cflags.append("-I%s" % usb_inc)
        tc.extra_cxxflags.append("-I%s" % usb_inc)
        tc.blocks["prefer_config_off"] = PreferConfigOffBlock
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # The snapshot declares cmake_minimum_required(VERSION 3.0); CMake >= 4
        # dropped compatibility below 3.5 (patch 0003 also raises it).
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        # R9: conservative parallelism; tools.build:jobs can raise it.
        jobs = self.conf.get("tools.build:jobs", default=2)
        cmake.build(cli_args=[f"-j{jobs}"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream ships COPYING.LIB (LGPL-2.1).
        from conan.tools.files import copy
        copy(self, "COPYING.LIB", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Application package: the driver executable plus the INDI descriptor.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        # libindi is published static-first, so Conan does not put its lib
        # directory into the run environment while the driver links libindi's
        # shared objects; declare the run-time search path (same as indi-fli/sx).
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH",
            self.dependencies["libindi"].cpp_info.libdirs[0])
