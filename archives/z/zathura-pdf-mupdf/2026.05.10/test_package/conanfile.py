#!/usr/bin/env python3
"""Conan test_package for zathura-pdf-mupdf — verifies plugin .so artifact.

The plugin is a shared module loaded by zathura at runtime. This test:
  1. Locates libpdf-mupdf.so in the conan package
  2. Verifies it's a valid ELF file with reasonable size (> 1MB, includes mupdf)
"""
import os
import glob

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ZathuraPdfMupdfTestConan(ConanFile):
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
        # Find the plugin .so in the conan package
        pkg = self.dependencies["zathura-pdf-mupdf"]
        so_path = None
        for libdir in pkg.cpp_info.libdirs:
            pattern = os.path.join(pkg.package_folder, libdir, "libpdf-mupdf.so")
            matches = glob.glob(pattern)
            if matches:
                so_path = matches[0]
                break
        if not so_path:
            pattern = os.path.join(pkg.package_folder, "**", "libpdf-mupdf.so")
            matches = glob.glob(pattern, recursive=True)
            if matches:
                so_path = matches[0]
        if not so_path:
            raise Exception("libpdf-mupdf.so not found in package")

        os.environ["PLUGIN_SO_PATH"] = so_path
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_zathura_pdf_mupdf")
        self.run(f'"{test_bin}"')
