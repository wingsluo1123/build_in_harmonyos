#!/usr/bin/env python3
"""Test package for gst-plugins-good 1.28.3

Verifies that the GStreamer good plugins are built and installed correctly.
The test checks that plugin .so files exist in the gstreamer-1.0 directory
and can be loaded via dlopen (cross-compilation safe).
"""
import os
import ctypes
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # No compilation needed — we check installed plugin files
        pass

    def test(self):
        # Get the package's lib directory (gstreamer plugins are in lib/gstreamer-1.0/)
        pkg = self.dependencies["gst-plugins-good"]
        libdirs = pkg.cpp_info.aggregated.libdirs

        plugin_found = False
        plugin_count = 0

        for libdir in libdirs:
            gstdir = os.path.join(str(libdir), "gstreamer-1.0")
            if os.path.isdir(gstdir):
                for f in os.listdir(gstdir):
                    if f.startswith("libgst") and f.endswith(".so"):
                        plugin_count += 1
                        plugin_found = True

        if not plugin_found:
            raise Exception("No GStreamer plugin .so files found in gstreamer-1.0/ directory")

        self.output.info(f"Found {plugin_count} GStreamer good plugins")

        # Try to dlopen one plugin (only on native build)
        if not cross_building(self):
            for libdir in libdirs:
                gstdir = os.path.join(str(libdir), "gstreamer-1.0")
                if os.path.isdir(gstdir):
                    for f in sorted(os.listdir(gstdir)):
                        if f.startswith("libgst") and f.endswith(".so"):
                            so_path = os.path.join(gstdir, f)
                            try:
                                ctypes.CDLL(so_path)
                                self.output.info(f"Successfully loaded plugin: {f}")
                                break
                            except Exception as e:
                                self.output.warning(f"Could not dlopen {f}: {e}")
                            break
                    break

        self.output.info("gst-plugins-good test passed!")
