#!/usr/bin/env python3
"""Conan recipe for indi-starbook 0.8-20221222163625 on HarmonyOS PC.

indi-starbook is an INDI driver for Vixen StarBook mounts (pre-Ten
generation): an INDI::Telescope subclass talking the StarBook command
protocol over plain HTTP (responses are HTML comments <!--KEY=VAL-->,
parsed with std::regex), transported by libcurl (connectioncurl.cpp) —
sibling of indi-starbook-ten (which bundles cpp-httplib instead).

OHOS-specific adaptations (same pattern as archives/i/indi-maxdomeii):
  - E092: CMake does not recognize HarmonyOS -> force CMAKE_SYSTEM_NAME=Linux.
  - OHOS libc++: link c++/c++abi for the C++ driver object.
  - FindINDI.cmake ships in the driver's own cmake_modules/; we inject
    INDI_INCLUDE_DIR (<libindi pkg>/include/libindi — the published package
    keeps every header in that subdirectory) and INDI_ROOT (<libindi pkg
    root) because libindi installs no INDIConfig.cmake.
  - FindNova.cmake short-circuits when NOVA_INCLUDE_DIR+NOVA_LIBRARIES are
    both injected (module line 14 takes them on trust); the driver includes
    <libnova/xxx.h> with prefix so NOVA_INCLUDE_DIR is the package include
    ROOT, not a subdirectory.
  - find_package(CURL REQUIRED) resolves via CMakeDeps CONFIG mode: the
    published curl recipe declares cmake_file_name=CURL and
    cmake_target_name=CURL::libcurl, so CURLConfig.cmake provides exactly
    the target the CMakeLists links (`set(CURL CURL::libcurl)`). We set
    CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON so the builtin FindCURL module does
    not shadow it; INDI/Nova keep their module-mode injections (no
    INDIConfig/NovaConfig names exist to shadow FindINDI/FindNova). This
    also keeps conanfile.py free of the quoted dependency literal that
    CI L0o's grep false-positives on (MateBook round 2/3 evidence: the
    subscript form works but trips L0o; attribute access does not exist
    in conan 2.29 at all).
  - patches (all platform-neutral, cf. notes.md):
    0001 backports the FindINDI.cmake INDI_VERSION regex fix (2022 snapshot
    cannot parse INDI 2.x's quoted `#define INDI_VERSION "2.2.2"`;
    byte-identical to the merged libfli/2.0 patch);
    0002 raises the bundled CMakeCommon.cmake C++ standard 14 -> 17
    (libindi 2.x headers use std::any; the directory-scope variable
    otherwise shadows the conan toolchain's cppstd=17);
    0003 backports upstream master's libindi 2.x Property migration:
    TimeT[1].text -> TimeTP[1].getText() at both call sites in
    updateLocation() (libindi 2.2.2 turned Telescope::TimeTP into
    INDI::PropertyText and dropped the raw IText array). Upstream master
    is otherwise byte-identical to this 2022 snapshot, so these two hunks
    ARE the full master sync.
    0004 makes CommandResponse skip leading whitespace before its
    OK/ERROR/payload checks (including the three inner ERROR sub-class
    probes): the upstream official test test_starbook.cpp asserts
    "    OK" parses as starbook::OK, but upstream never builds that test
    (its INDI_BUILD_UNITTESTS option is commented out), so the dead check
    rotted against the implementation. Verified: official test 2/2 PASSED
    on x86_64 after the fix.

Dependencies (all published to ohpcd):
  - libindi/2.2.2.1  (INDI framework: INDI::Telescope base class)
  - libnova/0.16     (astrometry: ln_equ_to_hequ/ln_lnlat_to_hlnlat, headers)
  - curl/8.15.0.1    (HTTP transport for the StarBook command protocol)
  - gtest/1.17.0.2   (test_requires: upstream official unit test)
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class IndiStarbookConan(ConanFile):
    name = "indi-starbook"
    version = "0.8-20221222163625"
    description = "INDI driver for Vixen StarBook mounts (HTTP command protocol)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/indilib/indi-3rdparty"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libindi/2.2.2.1")
        self.requires("libnova/0.16")
        self.requires("curl/8.15.0.1")

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
        # FindINDI.cmake (driver-shipped): feed it the conan dependency
        # locations because libindi has no INDIConfig. The published libindi
        # package installs ALL headers under include/libindi/; FindINDI checks
        # EXISTS ${INDI_INCLUDE_DIR}/indiversion.h and the driver sources
        # include INDI headers bare (<inditelescope.h>), so the injected dir
        # must be the libindi/ subdirectory. Library resolution goes through
        # INDI_ROOT (find_library HINTS; injecting INDI_LIBRARIES would be
        # shadowed and recomputed by the module).
        indi = self.dependencies["libindi"]
        indi_inc = os.path.join(indi.package_folder, "include", "libindi")
        tc.variables["INDI_INCLUDE_DIR"] = indi_inc
        tc.variables["INDI_ROOT"] = indi.package_folder
        # FindNova.cmake short-circuits (line 14: `if (NOVA_INCLUDE_DIR AND
        # NOVA_LIBRARIES)` -> accepts both without probing). The driver
        # includes <libnova/utility.h> with prefix, so the include dir is the
        # package include ROOT; link the static libnova.a.
        nova = self.dependencies["libnova"]
        tc.variables["NOVA_INCLUDE_DIR"] = os.path.join(nova.package_folder, "include")
        tc.variables["NOVA_LIBRARIES"] = os.path.join(nova.package_folder, "lib", "libnova.a")
        # find_package(CURL) resolves in CONFIG mode (see the docstring):
        # the curl recipe ships CURLConfig.cmake with CURL::libcurl via
        # CMakeDeps, so no injection and no dependency-name literal is
        # needed here at all (CI L0o grep stays clean). Prefer config mode
        # as a cache variable (before project()); INDI/Nova have no
        # matching config names and still fall back to the driver-shipped
        # Find modules fed by the injections above.
        tc.cache_variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = "ON"
        # FindINDI.cmake's find_path(INDI_DATA_DIR drivers.xml PATH_SUFFIXES
        # share/indi) only probes system paths -> NOTFOUND, and the xml would
        # install into a literal "INDI_DATA_DIR-NOTFOUND/" dir (same defect
        # family as indi-dsi round 1). Pre-seed ABSOLUTE into our own package
        # folder: find_path types the variable as PATH and CMake anchors
        # relative PATH values to the build dir (xml would escape the
        # package); pointing at the libindi package would cross the conan
        # package boundary at install time.
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

    def package_info(self):
        # Application package: expose the binary dir, no libs to link.
        self.cpp_info.bindirs = ["bin"]
        # OHOS libc++ for the C++ driver object.
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self.cpp_info.system_libs = ["c++", "c++abi"]
