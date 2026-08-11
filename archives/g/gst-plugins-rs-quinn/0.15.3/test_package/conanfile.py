#!/usr/bin/env python3
"""Conan test_package — gst-plugins-rs-quinn 0.15.3 (ELF symbol verification).

R34: the L1 test must actually exercise the packaged artifact. dlopen()
is unusable on OHOS for plugins whose transitive C deps (gstreamer) live
outside the musl ldso namespace (E186), so test.c parses the packaged
libgstquinn.so ELF directly and asserts its GStreamer plugin entry points
(gst_plugin_quinn_get_desc / gst_plugin_quinn_register) are exported.

E225: use cmake_layout(build_folder="$TMP") + user_presets_path=False so
Conan manages a unique temporary out-of-source build dir and no
CMakeUserPresets.json is written back into test_package/ source.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout, CMakeToolchain


class GstPluginsRsQuinnTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self, build_folder="$TMP")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.user_presets_path = False  # E225: never write presets back to source
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Locate the packaged plugin .so inside the dependency package
        dep = self.dependencies["gst-plugins-rs-quinn"]
        pkg_root = dep.package_folder
        plugin = os.path.join(pkg_root, "lib", "gstreamer-1.0", "libgstquinn.so")
        if not os.path.isfile(plugin):
            self.output.error(f"packaged plugin not found: {plugin}")
            raise SystemExit(1)

        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_gst-plugins-rs-quinn")
        self.run(f"{bin_path} {plugin}")
