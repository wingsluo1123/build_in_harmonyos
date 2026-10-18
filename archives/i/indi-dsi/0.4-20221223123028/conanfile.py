#!/usr/bin/env python3
"""Conan recipe for indi-dsi 0.4-20221223123028 on HarmonyOS PC.

indi-dsi is an INDI driver for Meade DSI/DSI II/DSI III (Pro & Color)
cameras: an INDI::CCD subclass talking USB bulk protocol directly via
libusb-1.0 (DsiDevice layer), uploading fx2 firmware at first connect.

OHOS-specific adaptations (same pattern as archives/i/indi-starbook):
  - E092: CMake does not recognize HarmonyOS -> force CMAKE_SYSTEM_NAME=Linux.
  - OHOS libc++: link c++/c++abi for the C++ driver object.
  - FindINDI.cmake ships in the driver's own cmake_modules/; inject
    INDI_INCLUDE_DIR (<libindi pkg>/include/libindi) + INDI_ROOT (<libindi
    pkg root) because libindi installs no INDIConfig.cmake.
  - FindCFITSIO.cmake short-circuits when CFITSIO_INCLUDE_DIR+
    CFITSIO_LIBRARIES are both injected (module line 17). The OHOS cfitsio
    package is STATIC and references zlib symbols (nm: deflate/deflateEnd/
    deflateInit2_), and the CMakeLists never adds zlib to the link line
    (its find_package(ZLIB REQUIRED) result is unused) — so libz.a is
    appended to the injected CFITSIO_LIBRARIES list, preserving link order.
  - FindUSB1.cmake: find_path/find_library become no-ops once
    USB1_INCLUDE_DIR/USB1_LIBRARY are pre-seeded (needs the include/
    libusb-1.0 subdir for its own <libusb.h> compile check). Separately,
    DsiDevice.h/download_fx2.h include <libusb-1.0/libusb.h> WITH prefix,
    so the package include ROOT goes on the compile line via extra_cxxflags
    (snapshot CMakeLists has no include_directories(${USB1_INCLUDE_DIR})).
  - Snapshot CMakeLists installs udev rules to /lib/udev/rules.d and the
    fx2 firmware to /lib/firmware as ABSOLUTE paths; both are overridden
    with package-relative share/ destinations (no upstream source change).
  - patches (all platform-neutral, cf. notes.md):
    0001 backports the FindINDI.cmake INDI_VERSION regex fix (2022 snapshot
    cannot parse INDI 2.x's quoted `#define INDI_VERSION "2.2.2"`;
    byte-identical to the merged libfli/2.0 patch);
    0002 raises the bundled CMakeCommon.cmake C++ standard 14 -> 17
    (libindi 2.x headers use std::any; the directory-scope variable
    otherwise shadows the conan toolchain's cppstd=17);
    0003 backports upstream master's libindi 2.x Property migration:
    IUSaveText(&BayerT[2], ...) -> BayerTP[2].setText(...) at both call
    sites (libindi 2.2.2 turned CCD::BayerTP into INDI::PropertyText and
    dropped the raw IText array). Upstream master is otherwise
    byte-identical to this 2022 snapshot in dsi_ccd.cpp/h, and the big
    DsiDevice.h restructure is NOT needed (snapshot header is
    self-consistent and carries no INDI includes), so these two hunks
    ARE the full required master sync.

Dependencies (all published to ohpcd):
  - libindi/2.2.2.1  (INDI framework: INDI::CCD base class)
  - cfitsio/4.6.4    (FITS image output; static lib, needs zlib at link)
  - libusb/1.0.27    (USB bulk transport for the DSI protocol)
  - zlib/1.3.1.1     (static libz.a, cfitsio link closure)
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class IndiDsiConan(ConanFile):
    name = "indi-dsi"
    version = "0.4-20221223123028"
    description = "INDI driver for Meade DSI/DSI II/DSI III cameras (USB)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/indilib/indi-3rdparty"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libindi/2.2.2.1")
        self.requires("cfitsio/4.6.4")
        self.requires("libusb/1.0.27")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not know HarmonyOS; present the target as Linux.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Upstream CMakeLists.txt declares cmake_minimum_required(VERSION 3.0),
        # which CMake >= 4.x rejects. Must be a cache variable (-D...) so it is
        # set before CMakeLists.txt is parsed (repo convention, cf. fast_obj).
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # FindINDI.cmake (driver-shipped): the published libindi package keeps
        # ALL headers under include/libindi/; FindINDI checks
        # EXISTS ${INDI_INCLUDE_DIR}/indiversion.h and the driver sources
        # include INDI headers bare (<indiccd.h>), so inject the subdirectory.
        # Library resolution goes through INDI_ROOT (find_library HINTS).
        indi = self.dependencies["libindi"]
        indi_inc = os.path.join(indi.package_folder, "include", "libindi")
        tc.variables["INDI_INCLUDE_DIR"] = indi_inc
        tc.variables["INDI_ROOT"] = indi.package_folder
        # FindCFITSIO.cmake short-circuits (line 17) when both vars are set.
        # The OHOS cfitsio package is STATIC and has undefined zlib symbols
        # (deflate family, nm-verified); the snapshot link line never adds
        # zlib, so append libz.a here — order matters (cfitsio first).
        cfits = self.dependencies["cfitsio"]
        zlib_ = self.dependencies["zlib"]
        tc.variables["CFITSIO_INCLUDE_DIR"] = os.path.join(cfits.package_folder, "include")
        tc.variables["CFITSIO_LIBRARIES"] = ";".join([
            os.path.join(cfits.package_folder, "lib", "libcfitsio.a"),
            os.path.join(zlib_.package_folder, "lib", "libz.a"),
        ])
        # find_package(ZLIB REQUIRED) result is unused by the link, but the
        # lookup itself must succeed — pre-seed the builtin module's vars.
        tc.variables["ZLIB_INCLUDE_DIR"] = os.path.join(zlib_.package_folder, "include")
        tc.variables["ZLIB_LIBRARY"] = os.path.join(zlib_.package_folder, "lib", "libz.a")
        # FindUSB1.cmake: pre-seeding USB1_INCLUDE_DIR/USB1_LIBRARY turns its
        # find_path/find_library into no-ops. The module's own compile check
        # includes <libusb.h> bare -> give it the include/libusb-1.0 subdir.
        usb = self.dependencies["libusb"]
        tc.variables["USB1_INCLUDE_DIR"] = os.path.join(usb.package_folder, "include", "libusb-1.0")
        tc.variables["USB1_LIBRARY"] = os.path.join(usb.package_folder, "lib", "libusb-1.0.so")
        # DsiDevice.h/download_fx2.h include <libusb-1.0/libusb.h> WITH prefix
        # (snapshot CMakeLists never adds USB1_INCLUDE_DIR to the include
        # path) -> put the package include ROOT on the compile line.
        tc.extra_cxxflags = [f"-I{os.path.join(usb.package_folder, 'include')}"]
        # Snapshot installs udev rules + fx2 firmware to ABSOLUTE /lib/...;
        # redirect both to package-relative share/. NOTE: upstream sets these
        # with an UNCONDITIONAL plain set() which shadows non-FORCE cache
        # injections — patch 0004 guards it with if(NOT DEFINED) so these
        # injected values survive (MateBook round 1: install wrote /lib/...
        # and died EPERM).
        tc.variables["RULES_INSTALL_DIR"] = "share/udev/rules.d"
        tc.variables["FIRMWARE_INSTALL_DIR"] = "share/firmware"
        # FindINDI.cmake's find_path(INDI_DATA_DIR drivers.xml PATH_SUFFIXES
        # share/indi) only probes system paths -> NOTFOUND, and the xml would
        # install into a literal "INDI_DATA_DIR-NOTFOUND/" dir. Pre-seed it.
        # Must be ABSOLUTE into our own package folder: find_path types the
        # variable as PATH, and CMake anchors RELATIVE -D/cache PATH values
        # to the build dir (WSL-verified: "share/indi" became
        # <build>/share/indi and the xml escaped the package). Pointing at
        # the LIBINDI package instead would cross the conan package boundary
        # at install time.
        tc.variables["INDI_DATA_DIR"] = os.path.join(
            self.package_folder, "share", "indi")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        build_jobs = self.conf.get("tools.build:jobs", default=2)
        cmake.build(cli_args=[f"-j{build_jobs}"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Ship the pure-std tokenize_str utility so test_package can compile
        # a real consumer probe (R34) against the driver's public helper —
        # no camera hardware needed.
        for f in ("Util.cpp", "Util.h"):
            copy(self, f, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "src"))

    def package_info(self):
        # Application package: expose the binary dir, no libs to link.
        self.cpp_info.bindirs = ["bin"]
        # OHOS libc++ for the C++ driver object.
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self.cpp_info.system_libs = ["c++", "c++abi"]
