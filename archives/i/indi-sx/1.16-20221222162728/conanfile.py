#!/usr/bin/env python3
"""Conan recipe for indi-sx 1.16-20221222162728 — INDI driver package for
Starlight Xpress hardware (CCD / filter wheel / active optics), shipped as a
subproject of the INDI 3rdparty tree (Debian Astronomy Team snapshot, see
conandata.yml).

The package product is the SX driver family:

  * bin/indi_sx_ccd    — CCD camera driver        (INDI::CCD)
  * bin/indi_sx_wheel  — filter wheel driver      (INDI::FilterWheel)
  * bin/indi_sx_ao     — active optics driver     (INDI::Focuser)
  * bin/sx_ccd_test    — upstream USB diagnostic tool shipped by the same tree
  * share/indi/indi_sx.xml — INDI driver descriptor (SX CCD / SX Wheel / SX AO)

Adaptation points for OHOS (full record in notes.md):
  * E092 — CMake has no HarmonyOS platform, so CMAKE_SYSTEM_NAME is forced to
    Linux and CMAKE_SYSTEM_PROCESSOR is pinned to aarch64.
  * CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF — the vendored cmake_modules/
    FindINDI.cmake / FindCFITSIO.cmake / FindUSB1.cmake must win over CONFIG
    lookups that CMakeToolchain enables by default.
  * INDI_ROOT points the vendored FindINDI.cmake at the pre-built libindi
    package instead of a system installation.
  * Patch 0001 backports the upstream FindINDI version regex (INDI >= 2.0
    writes `#define INDI_VERSION "2.2.2"` with quotes).
  * Patch 0002 raises the vendor CMakeCommon.cmake standard from C++14 to
    C++17 (INDI 2.x headers use std::any).
  * Patch 0003 fixes three build defects: cmake_minimum_required(3.0) is
    rejected by CMake >= 4, the upstream udev rules path is the absolute
    /lib/udev/rules.d (R49), and INDI_DATA_DIR has to be redirected so the
    driver descriptor is not installed into the libindi package.
  * Patch 0004 ports sxccd.cpp from the INDI 1.x property API to the 2.x one.

Upstream tests: none (the tree has no enable_testing()/add_test()); sx_ccd_test
is an interactive USB diagnostic utility, not a test suite.  The packaged
artefacts are verified by test_package/check_driver.py.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class PreferConfigOffBlock(Block):
    """Force CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF so the Find*.cmake modules
    vendored in the driver tree win over CONFIG package lookups."""
    template = "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)\n"


class IndisxConan(ConanFile):
    name = "indi-sx"
    version = "1.16-20221222162728"
    description = ("INDI driver package for Starlight Xpress CCD cameras, filter "
                   "wheels and active optics (INDI 3rdparty)")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/indilib/indi-3rdparty"
    url = "https://github.com/indilib/indi-3rdparty"
    topics = ("astronomy", "indi", "ccd", "filter-wheel", "active-optics", "driver")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Matches the upstream CMakeLists.txt: find_package(CFITSIO REQUIRED),
        # find_package(USB1 REQUIRED), find_package(INDI REQUIRED),
        # find_package(Threads REQUIRED).  The driver talks to the hardware
        # through libusb directly (sxccdusb.cpp), so libusb is a real link-time
        # requirement here, not just a transitive one.
        self.requires("libindi/2.2.2.1")
        self.requires("cfitsio/4.6.4")
        self.requires("libusb/1.0.27")
        # sxwheel.h includes <hidapi.h> with the bare name.
        self.requires("hidapi/0.15.0")

    @staticmethod
    def _hidapi_include(inc):
        """Directory that directly contains hidapi.h (layout differs per package)."""
        if os.path.isfile(os.path.join(inc, "hidapi.h")):
            return inc
        return os.path.join(inc, "hidapi")

    # R32: only Linux-family targets are supported.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"indi-sx is only supported on Linux/OHOS, not {self.settings.os}")

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
        # The upstream CMakeLists never adds USB1_INCLUDE_DIRS to the include
        # path (it relies on the system /usr/include), while sxccdusb.h includes
        # <libusb-1.0/libusb.h> — with the Conan package the version-prefixed
        # directory needs the include ROOT on the search path (same handling as
        # libfli in this repository).
        usb_inc = self.dependencies["libusb"].cpp_info.includedirs[0]
        if os.path.basename(usb_inc) == "libusb-1.0":
            usb_inc = os.path.dirname(usb_inc)
        tc.extra_cflags.append("-I%s" % usb_inc)
        tc.extra_cxxflags.append("-I%s" % usb_inc)
        # sxwheel.h includes <hidapi.h> with the bare name.
        hid_inc = self._hidapi_include(self.dependencies["hidapi"].cpp_info.includedirs[0])
        tc.extra_cflags.append("-I%s" % hid_inc)
        tc.extra_cxxflags.append("-I%s" % hid_inc)
        # The wheel talks to the hardware through hidapi (hid_open/hid_write/
        # hid_read), but the upstream CMakeLists only links USB1; put hidapi's
        # own libdir/libs on the link line (data-driven, no hardcoded names).
        for dep in ("hidapi", "libusb"):
            info = self.dependencies[dep].cpp_info
            for libdir in (info.libdirs or []):
                tc.extra_exelinkflags.append("-L%s" % libdir)
            for lib in (info.libs or []):
                tc.extra_exelinkflags.append("-l%s" % lib)
        # The upstream CMakeLists links the wheel against "rt" only when
        # CMAKE_SYSTEM_PROCESSOR matches "arm*"; aarch64 does not match, so the
        # POSIX realtime symbols have to be provided explicitly.  On OHOS/musl
        # librt is folded into libc, so link the libc-provided symbols by adding
        # the conan m/pthread closure instead of a bare -lrt.
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

    def package_info(self):
        # Application package: three drivers plus the upstream USB diagnostic
        # tool and the INDI device descriptor.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        # libindi is published static-first, so Conan does not put its lib
        # directory into the run environment while the drivers link libindi's
        # shared objects; declare the run-time search path (same handling as
        # indi-aok / indi-talon6 / indi-fli).
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH",
            self.dependencies["libindi"].cpp_info.libdirs[0])
