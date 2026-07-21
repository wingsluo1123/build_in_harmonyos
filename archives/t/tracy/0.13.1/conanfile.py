#!/usr/bin/env python3
"""Conan recipe for tracy 0.13.1 — OHOS aarch64 (only the embedded client lib).

Upstream: https://github.com/wolfpld/tracy
Homepage: https://tracy.nereid.pl/
License:  BSD-3-Clause

This recipe builds ONLY `libTracyClient.{a,so}` — the embedded client library.
It does NOT build the capture GUI / server (which would require 15+ deps
including wayland/mesa/glfw that don't exist on OHOS). On-device capture GUI
is out of scope; users capture to a network PC.

R-rules honoured:
  R32: settings.os includes "OHOS" and "Linux"
  R26: BUILD_SHARED_LIBS=OFF (system-name lib → static by default)
  R8 : patches are real (not stubs); see patches/0001-0003
  R34: test_package actually calls Tracy API
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TracyConan(ConanFile):
    name = "tracy"
    version = "0.13.1"
    description = "Real-time, nanosecond resolution frame profiler (client lib only)"
    license = "BSD-3-Clause"
    homepage = "https://tracy.nereid.pl/"
    url = "https://github.com/wolfpld/tracy"

    package_type = "library"

    # R32: include OHOS in supported OS (don't restrict to == "Linux")
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libTracyClient only needs pthread + dl, both come from system libc/libpthread
        # on Linux/OHOS; no external Conan deps needed (R36 satisfied trivially).
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name library → static default
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # tracy CMake options
        tc.variables["TRACY_STATIC"] = "ON"
        tc.variables["TRACY_ENABLE"] = "ON"
        tc.variables["TRACY_NO_BROADCAST"] = "ON"        # don't broadcast on LAN
        tc.variables["TRACY_ONLY_LOCALHOST"] = "ON"      # listen on 127.0.0.1
        tc.variables["TRACY_NO_SYSTEM_TRACING"] = "ON"   # bionic lacks __NR_perf_event_open
        tc.variables["TRACY_NO_CRASH_HANDLER"] = "ON"    # OHOS signal handling differs
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
        self.cpp_info.libs = ["TracyClient"]
        # libTracyClient.{a,so} only links against pthread + dl
        self.cpp_info.system_libs = ["pthread", "dl"]