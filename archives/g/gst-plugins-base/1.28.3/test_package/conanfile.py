#!/usr/bin/env python3
"""Test package for gst-plugins-base 1.28.3"""
import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        pkg = self.dependencies["gst-plugins-base"]
        libdirs = pkg.cpp_info.aggregated.libdirs
        found = False
        for libdir in libdirs:
            gstdir = os.path.join(str(libdir), "gstreamer-1.0")
            if os.path.isdir(gstdir):
                for f in os.listdir(gstdir):
                    if f.startswith("libgst") and f.endswith(".so"):
                        found = True
                        self.output.info(f"Found plugin: {f}")
            else:
                # Check if libdir itself has .so files
                if os.path.isdir(str(libdir)):
                    for f in os.listdir(str(libdir)):
                        if f.startswith("libgst") and (f.endswith(".so") or f.endswith(".a")):
                            found = True
                            self.output.info(f"Found library: {f}")
                            break
        if not found:
            raise Exception("No gst-plugins-base libraries found")
        self.output.info("gst-plugins-base test passed!")
