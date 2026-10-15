#!/usr/bin/env python3
"""indi-playerone 0.9 — INDI driver for PlayerOne Astronomy (POA) CCD cameras.

The driver lives in the indi-3rdparty monorepo (subdirectory indi-playerone/)
and its CMakeLists appends "../cmake_modules" to CMAKE_MODULE_PATH, so the
whole repository tree has to be kept (source strip_root=True).

Adaptation points for OHOS (see notes.md):
  * E092 — CMake does not know the HarmonyOS platform, so CMAKE_SYSTEM_NAME is
    forced to Linux and CMAKE_SYSTEM_PROCESSOR is pinned to aarch64 (same
    workaround proven for libindi/2.2.2.1, indi-gpsnmea and indi-fishcamp in
    this repo).
  * CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF — Conan's CMakeToolchain defaults to
    ON, which shadows the Find*.cmake modules vendored in
    indi-playerone/cmake_modules/ (FindINDI / FindPLAYERONE / FindCFITSIO /
    FindUSB1) and would make CMake hunt for upstream CONFIG packages that do
    not exist for OHOS.
  * FindPLAYERONE.cmake locates the vendor SDK through PlayerOneCamera.h
    (PATH_SUFFIXES libplayerone) and libPlayerOneCamera — both provided by
    the libplayerone/3.1.0 package (install-imported vendor prebuilt).
  * The 0.9 snapshot (2023-01-05) already targets the INDI 2.x C++ API
    (setExposureDuration / addCaptureFormat / INDI::PropertyText getState),
    so no INDI 1.x -> 2.x API porting patch is needed, unlike indi-fishcamp.

The only executable artifacts are bin/indi_playerone_ccd (the driver) and
bin/playerone_camera_test (the vendor SDK test utility), plus the device
descriptor share/indi/indi_playerone.xml.
"""
import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class PreferConfigOffBlock(Block):
    """Force CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF so the vendored Find*.cmake
    modules win over non-existent upstream CONFIG packages (the block runs
    last, overriding the toolchain's default ON)."""
    template = textwrap.dedent("""\
        set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)
    """)


class IndiPlayeroneConan(ConanFile):
    name = "indi-playerone"
    version = "0.9"
    description = "INDI driver for PlayerOne Astronomy (POA) CCD cameras (vendor libPlayerOneCamera SDK)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/indilib/indi-3rdparty"
    url = "https://github.com/indilib/indi-3rdparty"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*"

    # R32: only Linux-family targets are supported.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"indi-playerone is only supported on Linux/OHOS, not {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Real build-time and runtime dependencies, per upstream CMakeLists.txt:
        # find_package(INDI REQUIRED) / find_package(PLAYERONE REQUIRED) /
        # find_package(CFITSIO REQUIRED) / find_package(ZLIB REQUIRED) /
        # find_package(USB1 REQUIRED) / find_package(Threads REQUIRED).
        self.requires("libindi/2.2.2.1")
        self.requires("libplayerone/3.1.0")
        self.requires("cfitsio/4.6.4")
        self.requires("zlib/1.3.1.1")
        self.requires("libusb/1.0.27")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake has no HarmonyOS platform; drive the Linux path instead.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        # Make the vendored Find*.cmake modules win over CONFIG lookups.
        tc.blocks["prefer_config_off"] = PreferConfigOffBlock
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Upstream CMakeLists.txt declares cmake_minimum_required(VERSION 3.0)
        # and CMake >= 4.0 removed compatibility with anything below 3.5. It
        # MUST be passed as a real -D cache variable (see indi-gpsnmea /
        # indi-fishcamp conanfile for why tc.variables is not enough here).
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        # R9: conservative parallelism; tools.build:jobs can raise it.
        jobs = self.conf.get("tools.build:jobs", default=2)
        cmake.build(cli_args=[f"-j{jobs}"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # The Debian orig tarball ships COPYING.LGPL; copy it into the package
        # license dir so the license is distributed with the binary.
        licenses = os.path.join(self.source_folder, "COPYING.LGPL")
        if os.path.isfile(licenses):
            import shutil
            os.makedirs(os.path.join(self.package_folder, "licenses"),
                        exist_ok=True)
            shutil.copy(licenses, os.path.join(self.package_folder,
                                               "licenses", "COPYING.LGPL"))

    def package_info(self):
        # Application package: the only artifacts are the driver executable,
        # the vendor SDK test utility and the INDI device descriptor.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
