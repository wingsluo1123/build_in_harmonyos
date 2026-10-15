#!/usr/bin/env python3
"""Conan recipe for indi-starbook-ten 0.1 on HarmonyOS PC.

indi-starbook-ten is an INDI driver for the Vixen StarBook Ten telescope
mount controller (firmware >= 5.10). It is a small C++ executable
(indi_starbook_ten.cpp + starbook_ten.cpp + connectionhttp.cpp, plus a
bundled cpp-httplib header) that links the published libindi and libnova
packages. The mount is driven over HTTP (StarBook protocol).

OHOS-specific adaptations (same pattern as archives/i/indi-rtklib):
  - E092: CMake does not recognize HarmonyOS -> force CMAKE_SYSTEM_NAME=Linux
    (same as libindi recipe).
  - OHOS libc++ : link c++/c++abi for the C++ driver object.
  - FindINDI.cmake / FindNova.cmake ship in the driver's own cmake_modules/;
    we inject INDI_INCLUDE_DIR/INDI_ROOT/NOVA_* pointing at the conan
    dependency package folders because the published libindi recipe does
    not install an INDIConfig.cmake. INDI_INCLUDE_DIR must be the
    include/libindi/ subdirectory (the published package keeps every header
    there) or FindINDI's indiversion.h check aborts the configure.
  - patches (all platform-neutral, cf. notes.md):
    0001 backports the upstream FindINDI.cmake INDI_VERSION regex fix
    (2022 snapshot cannot parse INDI 2.x's quoted `#define INDI_VERSION
    "2.2.2"`; byte-identical to the merged libfli/2.0 patch);
    0002 raises the bundled CMakeCommon.cmake C++ standard 14 -> 17
    (libindi 2.x headers use std::any; the directory-scope variable
    otherwise shadows the conan toolchain's cppstd=17);
    0003 backports upstream master's libindi 2.x Property-API migration
    of indi_starbook_ten.cpp (plus the fabs() coordinate fix in
    starbook_ten.cpp) — the 2021 sources do not compile against
    libindi 2.2.2 otherwise.

Dependencies (all published to ohpcd):
  - libindi/2.2.2.1  (INDI framework: INDI::Telescope base class)
  - libnova/0.16     (celestial math: ln_deg_to_dms/ln_dms_to_deg)
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class IndiStarbookTenConan(ConanFile):
    name = "indi-starbook-ten"
    version = "0.1"
    description = "INDI driver for the Vixen StarBook Ten telescope mount controller"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/indilib/indi-3rdparty"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libindi/2.2.2.1")
        self.requires("libnova/0.16")

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
        # The driver ships its own FindINDI.cmake / FindNova.cmake; feed them
        # the conan dependency locations because libindi has no INDIConfig.
        indi = self.dependencies["libindi"]
        nova = self.dependencies["libnova"]
        # The published libindi package installs ALL headers under
        # include/libindi/ (verified against the ohpcd artifact). FindINDI.cmake
        # checks EXISTS ${INDI_INCLUDE_DIR}/indiversion.h and the driver sources
        # include INDI headers bare (<inditelescope.h>), so the injected dir
        # must be the libindi/ subdirectory — injecting the include root fails
        # the version-header check ("INDI version header not found").
        indi_inc = os.path.join(indi.package_folder, "include", "libindi")
        # FindINDI.cmake resolves its default driver+align component libraries
        # via find_library(... HINTS ${INDI_ROOT} PATH_SUFFIXES lib64 lib);
        # lib/ holds libindidriver and libindiAlignmentDriver (the default
        # component set). An injected INDI_LIBRARIES cache variable would be
        # shadowed and recomputed by the module, so point INDI_ROOT at the
        # package folder instead.
        nova_inc = os.path.join(nova.package_folder, "include")
        nova_lib = os.path.join(nova.package_folder, "lib")
        tc.variables["INDI_INCLUDE_DIR"] = indi_inc
        tc.variables["INDI_ROOT"] = indi.package_folder
        # The driver sources include libnova headers version-prefixed
        # (<libnova/julian_day.h>), so NOVA_INCLUDE_DIR must be the include
        # ROOT (not include/libnova). FindNova.cmake trusts both injected
        # variables without searching.
        tc.variables["NOVA_INCLUDE_DIR"] = nova_inc
        tc.variables["NOVA_LIBRARIES"] = os.path.join(nova_lib, "libnova.a")
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
        # Ship the StarBook protocol client + bundled httplib so test_package
        # can compile a real consumer probe (R34) against a localhost mock
        # mount — no telescope hardware needed.
        for f in ("starbook_ten.cpp", "starbook_ten.h", "httplib.h"):
            copy(self, f, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "src"))

    def package_info(self):
        # Application package: expose the binary dir, no libs to link.
        self.cpp_info.bindirs = ["bin"]
        # OHOS libc++ for the C++ driver object.
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self.cpp_info.system_libs = ["c++", "c++abi"]
