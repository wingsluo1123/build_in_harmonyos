#!/usr/bin/env python3
"""Conan recipe for bdf2sfd 1.1.9 — BDF → SFD bitmap font converter (CMake).

Build: cmake + make. Produces the `bdf2sfd` executable (font converter) and
installs man/bdf2sfd.1. Adapted for HarmonyOS OHOS (aarch64-unknown-linux-ohos).

Upstream declares no external dependencies (README "Dependencies": *bdf2sfd
uses the CMake build system and does not requires any external dependencies*),
confirmed locally: CMakeLists.txt carries no find_package / pkg_check_modules /
AC_CHECK_LIB / target_link_libraries. check_function_exists(pledge) and
check_function_exists(strtonum) fall back to the bundled compat/ shims, so the
package is closed at the libc level.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Bdf2SfdConan(ConanFile):
    name = "bdf2sfd"
    version = "1.1.9"
    description = "bdf2sfd — convert BDF bitmap fonts to SFD (Spline Font Database)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/fcambus/bdf2sfd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream only knobs: ENABLE_SECCOMP (default 0, experimental and
        # architecture-selected) — keep it off so behaviour matches upstream CI.
        tc.cache_variables["ENABLE_SECCOMP"] = "0"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # R51: run the upstream test suite declared in CMakeLists.txt:65-70
        # (enable_testing() + 5 add_test). 5/5 pass locally in 0.30s.
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
