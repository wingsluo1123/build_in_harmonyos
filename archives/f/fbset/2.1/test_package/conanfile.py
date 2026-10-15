#!/usr/bin/env python3
"""Conan test_package — fbset/2.1 consumer verification (R34).

fbset is a command line tool and ships no library to link against, so the
test binary receives the path of the packaged `fbset` executable as argv[1]
and drives it end to end:

  1. `fbset --help`  → exit status 0 plus banner/usage output,
  2. `fbset -V`      → the 2.1 version banner,
  3. `fbset -s`      → a real frame-buffer query, i.e. the FBIOGET_VSCREENINFO
                       ioctl path: on a machine with /dev/fb* the video mode
                       is printed, otherwise the program must emit its
                       well-formed device diagnostic.

Removing the package artifacts makes execve() fail inside the test, so the
consumer test also covers the CI destructive negative check (L1e).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FbsetTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
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
        fbset_bin = os.path.join(
            self.dependencies["fbset"].package_folder, "bin", "fbset"
        )
        test_bin = os.path.join(self.build_folder, "test_fbset")
        self.run(f'"{test_bin}" "{fbset_bin}"', env="conanrun")
