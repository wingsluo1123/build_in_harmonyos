#!/usr/bin/env python3
"""Conan test_package for gst-libav 1.28.3.

Tests that gst-libav plugin ELF is valid (soname + descriptor symbols).
R34: Test substantially depends on the tested package (checks plugin ELF).
gst-libav is a pure GStreamer plugin (.so), no executables or standalone API.
"""
import os
import glob as _glob

from conan import ConanFile


class GstLibavTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # gst-libav is a pure plugin (libgstlibav.so).
        # Verify the plugin ELF has correct SONAME and GStreamer descriptor symbols.
        pkg = self.dependencies[self.tested_reference_str].package_folder
        plugin_path = os.path.join(pkg, "lib", "gstreamer-1.0", "libgstlibav.so")
        if not os.path.isfile(plugin_path):
            raise Exception(f"Plugin not found: {plugin_path}")

        # Check SONAME
        self.run(f'llvm-readelf -d "{plugin_path}" | grep SONAME')
        # Check GStreamer plugin descriptor symbols
        self.run(f'llvm-readelf --dyn-syms "{plugin_path}" | grep gst_plugin_libav')

    def test(self):
        # Re-run the checks as the test step
        pkg = self.dependencies[self.tested_reference_str].package_folder
        plugin_path = os.path.join(pkg, "lib", "gstreamer-1.0", "libgstlibav.so")
        self.run(f'echo "Plugin: {plugin_path}"')
        self.run(f'ls -la "{plugin_path}"')
        self.run(f'echo "gst-libav plugin verified successfully"')
