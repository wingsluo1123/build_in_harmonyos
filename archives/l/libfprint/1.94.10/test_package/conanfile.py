#!/usr/bin/env python3
"""Conan test_package — libfprint 1.94.10 L1 test.

Compiles and runs a C consumer that calls the real libfprint public API
(fp_context_new / fp_context_enumerate / fp_context_get_devices /
fp_device_get_driver / fp_device_get_name), verifying headers, linking and
runtime behaviour without any fingerprint hardware. In the OHOS sandbox there
is no USB backend, so the device list is legitimately empty; the test asserts
that discovery completes and yields a valid (possibly empty) array instead of
aborting (no platform-specific conditional compilation).

CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/l/libfprint/1.94.10/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibfprintTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # test.c uses glib-2.0 directly (g_printerr / G_TYPE_CHECK_INSTANCE_TYPE)
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(self.cpp.build.bindirs[0], "test_libfprint" + suffix)
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
