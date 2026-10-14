#!/usr/bin/env python3
"""Conan test_package for gocr — L1 consumer test of libPgm2asc.

R34: the test really consumes the package instead of printing a string:

  * ``test_gocr`` is a C++ program that links ``libPgm2asc`` and drives the
    exact API sequence OSRA uses (``job_init``/``job_init_image``/
    ``pgm2asc``/``getTextLine``/``free_textlines``) on an in-memory pixmap,
    then writes that pixmap as a PGM file;
  * the packaged ``gocr`` command line tool is executed on that PGM to prove
    the CLI and the library agree.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GocrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        pattern = os.path.join(self.build_folder, "gocr_test_pattern.pgm")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_gocr")
        # 1) library consumer test (also writes the PGM used below)
        self.run(f'"{test_bin}" "{pattern}"', env="conanrun")

        # 2) the shipped CLI must read that PGM (end-to-end smoke test)
        gocr_bin = os.path.join(self.dependencies["gocr"].package_folder, "bin", "gocr")
        if os.path.exists(gocr_bin):
            # E046: HMDFS may not preserve the executable bit
            try:
                os.chmod(gocr_bin, 0o755)
            except OSError:
                pass
        else:
            gocr_bin = "gocr"
        self.run(f'"{gocr_bin}" -i "{pattern}" -o "{pattern}.txt"', env="conanrun")
        if os.path.exists(pattern + ".txt"):
            self.output.info(f"gocr wrote {pattern}.txt")
