#!/usr/bin/env python3
"""Conan test_package for audiotube v26.04.1 — ytm library verification.

Verifies that the ytm static library and ytmusic.h header are correctly
installed from the audiotube package. Uses self.run() to check file
existence and library symbols, ensuring genuine dependency on the package.
"""
import os

from conan import ConanFile


class AudiotubeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        lib_dir = self.dependencies["audiotube"].cpp_info.libdirs[0]
        inc_dir = self.dependencies["audiotube"].cpp_info.includedirs[0]
        pkg_folder = self.dependencies["audiotube"].package_folder

        lib_path = os.path.join(pkg_folder, lib_dir, "libytm.a")
        inc_path = os.path.join(pkg_folder, inc_dir, "ytmusic.h")

        # Verify library file exists (genuine dependency check)
        self.run(f"test -f {lib_path}", env="conanrun")
        # Verify header file exists
        self.run(f"test -f {inc_path}", env="conanrun")
        # Verify the library contains YTMusic symbols
        self.run(f"nm {lib_path} | grep YTMusic", env="conanrun")
