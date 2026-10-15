#!/usr/bin/env python3
"""Package test (L1) for xtrkcad.

Two checks are run, both of them really execute something that was packaged:

1. A consumer program is built against the package's CMake package files and
   linked with a packaged library, then executed.
2. The rasteriser that took the place of Inkscape on OpenHarmony (svg2png,
   built from the sources this recipe patches in) is executed on a small SVG
   and its PNG output is verified.  This is the piece of the adaptation the
   toolbar bitmaps of the application depend on.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import save


class XtrkcadTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe = os.path.join(self.cpp.build.bindirs[0], "test_xtrkcad")
        self.run(exe, env="conanrun")

        svg = os.path.join(self.build_folder, "check.svg")
        png = os.path.join(self.build_folder, "check.png")
        save(self, svg,
             '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16">'
             '<rect width="16" height="16" fill="#00ff00"/></svg>')
        self.run('svg2png "{}" -h 24 -o "{}"'.format(svg, png), env="conanrun")
        with open(png, "rb") as handle:
            header = handle.read(8)
        assert header == b"\x89PNG\r\n\x1a\n", "svg2png did not produce a PNG file"
