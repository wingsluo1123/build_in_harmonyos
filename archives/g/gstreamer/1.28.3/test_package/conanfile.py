#!/usr/bin/env python3
"""Test package for gstreamer 1.28.3"""
import os
import ctypes
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        pkg = self.dependencies["gstreamer"]
        libdirs = pkg.cpp_info.aggregated.libdirs
        found = False
        for libdir in libdirs:
            for f in os.listdir(str(libdir)):
                if f.startswith("libgstreamer-1.0") and (f.endswith(".so") or f.endswith(".a")):
                    found = True
                    self.output.info(f"Found library: {f}")
                    break
        if not found:
            raise Exception("libgstreamer-1.0 not found in package")
        self.output.info("gstreamer test passed!")
