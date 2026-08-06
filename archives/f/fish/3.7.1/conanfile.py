#!/usr/bin/env python3
"""Conan recipe for fish 3.7.1 — the friendly interactive shell.

Fish uses CMake as its build system. It produces three executables:
fish, fish_indent, and fish_key_reader. PCRE2 is bundled via FetchContent.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class FishConan(ConanFile):
    name = "fish"
    version = "3.7.1"
    description = "fish - the friendly interactive shell"
    license = "GPL-2.0-only"
    homepage = "https://fishshell.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    build_policy = "missing"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Fish requires ncurses for terminal handling.
        # On HarmonyOS, ncurses is available from the OHOS SDK.
        # If ncurses conan package exists, use it; otherwise CMake find_package handles it.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Download PCRE2 source for FetchContent (GitHub not accessible on OHOS)
        pcre2_url = "https://gitcode.com/PCRE2Project/pcre2/releases/download/pcre2-10.36/pcre2-10.36.tar.bz2"
        pcre2_dir = os.path.join(self.source_folder, "_pcre2_src")
        get(self, url=pcre2_url, strip_root=True, destination=pcre2_dir)

    def generate(self):
        tc = CMakeToolchain(self)
        # Disable gettext (not available on HarmonyOS)
        tc.cache_variables["WITH_GETTEXT"] = "OFF"
        # Use bundled PCRE2 (system PCRE2 not available)
        tc.cache_variables["FISH_USE_SYSTEM_PCRE2"] = "OFF"
        # CMake 4.x compatibility
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Provide PCRE2 local source (bypass FetchContent GitHub download)
        pcre2_dir = os.path.join(self.source_folder, "_pcre2_src")
        if os.path.isdir(pcre2_dir):
            tc.cache_variables["FETCHCONTENT_SOURCE_DIR_PCRE2"] = pcre2_dir
        # TPUTS_USES_INT_ARG: CMake check fails without curses lib linked;
        # ncurses on OHOS uses int parameter, so force-enable
        tc.cache_variables["TPUTS_USES_INT_ARG"] = "ON"
        # Provide ncurses paths if available from system or prior build
        ncurses_prefix = os.environ.get("NCURSES_PREFIX", "")
        if ncurses_prefix and os.path.isdir(ncurses_prefix):
            inc = os.path.join(ncurses_prefix, "include")
            lib = os.path.join(ncurses_prefix, "lib", "libncursesw.a")
            if not os.path.exists(lib):
                lib = os.path.join(ncurses_prefix, "lib", "libncurses.a")
            if os.path.exists(inc) and os.path.exists(lib):
                tc.cache_variables["CURSES_INCLUDE_DIR"] = inc
                tc.cache_variables["CURSES_INCLUDE_DIRS"] = inc
                tc.cache_variables["CURSES_LIBRARY"] = lib
                tc.cache_variables["CURSES_CURSES_LIBRARY"] = lib
                tc.cache_variables["CURSES_NCURSES_LIBRARY"] = lib
                tc.cache_variables["CURSES_FOUND"] = "TRUE"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
