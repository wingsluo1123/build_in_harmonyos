#!/usr/bin/env python3
"""Conan test_package — perl-object-pad 0.821-r0

L1 test: verify Pad.so is a valid Perl XS shared library.
Compiles a C test that reads the ELF header to verify the .so is a
valid ELF64 AArch64 shared library, and checks for the boot_Object__Pad
symbol via nm.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import copy


class PerlobjectpadTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Copy test source to build folder (skip if already same dir)
        if os.path.abspath(self.source_folder) != os.path.abspath(self.build_folder):
            copy(self, "main.c", src=self.source_folder, dst=self.build_folder)

        # Find Pad.so in the package
        dep = self.dependencies["perl-object-pad"]
        pkg_folder = dep.package_folder
        so_files = glob.glob(
            os.path.join(pkg_folder, "**", "Pad.so"), recursive=True
        )
        if not so_files:
            raise Exception("FAIL: Pad.so not found in package")
        self._so_path = so_files[0]

    def test(self):
        dep = self.dependencies["perl-object-pad"]
        pkg_folder = dep.package_folder
        so_path = self._so_path

        self.output.info(f"Testing Pad.so at {so_path}")

        # Compile the test binary that verifies ELF structure
        self.run("clang -o test_pad main.c", env="conanbuild")

        # Run it against the actual .so from the package
        self.run(f"./test_pad {so_path}", env="conanbuild")

        # Verify the Perl XS bootstrap symbol exists
        self.run(f"nm -D {so_path} | grep -q boot_Object__Pad", env="conanbuild")
        self.output.info("PASS: boot_Object__Pad symbol found")

        # Verify header file exists and is non-empty
        header = os.path.join(pkg_folder, "include", "object_pad.h")
        if not os.path.exists(header):
            raise Exception("FAIL: object_pad.h not found in package")
        if os.path.getsize(header) == 0:
            raise Exception("FAIL: object_pad.h is empty")
        self.output.info(
            f"PASS: object_pad.h found ({os.path.getsize(header)} bytes)"
        )
