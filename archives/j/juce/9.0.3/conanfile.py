#!/usr/bin/env python3
"""Conan recipe — juce 9.0.3 (CMake, C++17 cross-platform audio/UI framework).

JUCE 9.x modules are INTERFACE libraries: the framework ships module headers
plus module source files, and consumers compile the module sources they need
into their own targets (this is JUCE's official consumption model — see
`juce_add_*` macros in JUCEUtils.cmake). Accordingly the recipe installs the
whole framework (headers + module sources + CMake support files) and declares
an include-only consumer-facing target.

OHOS platform notes (HarmonyOS PC, aarch64, musl libc):
  - OHOS toolchain predefines __linux__ so JUCE takes the JUCE_LINUX path;
    the CMake layer sees CMAKE_SYSTEM_NAME=HarmonyOS (conan OHOS mapping).
  - pthread_cancel is absent on OHOS musl → patched like the Android branch
    (see patches/0001, E127).
  - The OHOS sysroot ships no libcurl headers → JUCE_USE_CURL=0 is forced for
    consumers so juce_core compiles without <curl/curl.h> (juce_core bundles
    its own zlib via juce_core_zlib.c, so no external zlib needed).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class JuceConan(ConanFile):
    name = "juce"
    version = "9.0.3"
    description = "JUCE — cross-platform C++ framework for audio and graphical applications"
    license = "AGPL-3.0, commercial (JUCE 9 licence)"
    homepage = "https://juce.com/"
    url = "https://github.com/juce-framework/JUCE"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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
        # Framework-only: never configure/build extras (Projucer etc.) or examples.
        tc.variables["JUCE_BUILD_EXTRAS"] = "OFF"
        tc.variables["JUCE_BUILD_EXAMPLES"] = "OFF"
        # Skip helper-tool targets (lv2 manifest helper etc.) so the install
        # tree is self-contained without host toolchains.
        tc.variables["JUCE_BUILD_HELPER_TOOLS"] = "ON"
        tc.variables["JUCE_COPY_PLUGIN_AFTER_BUILD"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # JUCE modules are INTERFACE libraries (header + module-source model);
        # consumers compile the module sources into their own targets, so there
        # is nothing to compile here — configure() generates the install rules.
        # Building the default target would pull in juceaide (needs freetype,
        # absent on OHOS), which must not be part of the framework package.

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        modules_inc = "include/JUCE-9.0.3/modules"
        self.cpp_info.includedirs = [modules_inc]
        # OHOS sysroot has no libcurl headers; JUCE's curl-based networking is
        # unavailable on OHOS. Force JUCE_USE_CURL=0 so consumers compile the
        # framework without <curl/curl.h> (mirrors upstream's per-project config).
        self.cpp_info.defines = ["JUCE_USE_CURL=0"]
        # Header+module-source framework: no precompiled libraries to link.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []