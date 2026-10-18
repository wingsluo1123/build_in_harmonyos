#!/usr/bin/env python3
"""Conan recipe for tsctp 0.8.6 — SCTP test tool (C, CMake).

Upstream: https://github.com/dreibh/tsctp (TSCTP - An SCTP Test Tool).
Build: CMake -> one executable `tsctp` (src/tsctp.c) linked against the kernel
SCTP helper library (lksctp-tools: netinet/sctp.h + libsctp).

OHOS adaptation
---------------
1. Upstream CMakeLists.txt only whitelists Linux/FreeBSD/NetBSD/Darwin. The
   OHOS Conan profile maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS, so upstream
   aborted during configure with:
       CMake Error at CMakeLists.txt:73 (MESSAGE):
         HarmonyOS not supported (yet?)
   patches/0001-CMakeLists.txt.patch registers HarmonyOS as a Linux-compatible
   system and extends the REQUIRED libsctp lookup to it (same code path as
   Linux — HarmonyOS uses the Linux socket ABI).
2. netinet/sctp.h and libsctp come from the Conan dependency
   lksctp-tools/1.0.21 (upstream Debian Build-Depends: libsctp-dev >= 1.0.5).
   Its include/ and lib/ directories are handed to CMake through
   CMAKE_REQUIRED_INCLUDES / CMAKE_LIBRARY_PATH (+ -I in CMAKE_C_FLAGS), so
   upstream's own CHECK_INCLUDE_FILE(netinet/sctp.h) and
   FIND_LIBRARY(SCTP_LIB sctp REQUIRED) keep working unmodified.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.microsoft import is_msvc


class TsctpConan(ConanFile):
    name = "tsctp"
    version = "0.8.6"
    description = ("tsctp — SCTP test tool: performs basic SCTP functionality tests to check "
                   "implementation interoperability and verify that the SCTP stack is working")
    license = "BSD-3-Clause AND GPL-3.0-or-later"
    homepage = "https://www.nntb.no/~dreibh/tsctp/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Debian Build-Depends: libsctp-dev (>= 1.0.5) — provides netinet/sctp.h
        # and libsctp. The OHOS binary is published in the ohpcd repository.
        self.requires("lksctp-tools/1.0.21")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32: OHOS is Linux-compatible; never compare settings.os == "Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} requires the Linux SCTP socket API (netinet/sctp.h); "
                f"{self.settings.os} is not supported")
        if is_msvc(self):
            raise ConanInvalidConfiguration(f"{self.ref} does not build with MSVC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # Upstream resolves netinet/sctp.h + libsctp with plain CMake probes, so
        # point those probes at the Conan-managed lksctp-tools package instead of
        # reworking the upstream CMake logic.
        dep = self.dependencies["lksctp-tools"]
        components = dep.cpp_info.aggregated_components()
        includedirs = [os.path.join(dep.package_folder, d).replace("\\", "/")
                       for d in components.includedirs]
        libdirs = [os.path.join(dep.package_folder, d).replace("\\", "/")
                   for d in components.libdirs]

        # CHECK_INCLUDE_FILE(netinet/sctp.h ...) probe
        tc.cache_variables["CMAKE_REQUIRED_INCLUDES"] = ";".join(includedirs)
        # FIND_LIBRARY(SCTP_LIB sctp REQUIRED) probe
        tc.cache_variables["CMAKE_LIBRARY_PATH"] = ";".join(libdirs)
        # Actual compilation of src/tsctp.c
        tc.extra_cflags = [f"-I{d}" for d in includedirs]

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING-BSD", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING-GPL", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "tsctp")
        self.cpp_info.set_property("cmake_target_name", "tsctp::tsctp")
