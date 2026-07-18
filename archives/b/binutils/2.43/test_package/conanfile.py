#!/usr/bin/env python3
"""Conan test_package for binutils 2.43 i686-elf cross toolchain.

Tests that the cross-binutils tools (i686-elf-ld, i686-elf-as, etc.)
are properly built and executable.
"""
import os

from conan import ConanFile


class BinutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: test must substantially call the tested package's binaries
        bin_dir = os.path.join(self.dependencies["binutils"].package_folder, "bin")

        # Test i686-elf-ld
        ld_path = os.path.join(bin_dir, "i686-elf-ld")
        self.run(f"{ld_path} --version", env="conanrun")

        # Test i686-elf-as
        as_path = os.path.join(bin_dir, "i686-elf-as")
        self.run(f"{as_path} --version", env="conanrun")

        # Test i686-elf-objdump
        objdump_path = os.path.join(bin_dir, "i686-elf-objdump")
        self.run(f"{objdump_path} --version", env="conanrun")

        # Test i686-elf-nm
        nm_path = os.path.join(bin_dir, "i686-elf-nm")
        self.run(f"{nm_path} --version", env="conanrun")

        # Test i686-elf-ar
        ar_path = os.path.join(bin_dir, "i686-elf-ar")
        self.run(f"{ar_path} --version", env="conanrun")

        # Verify all expected tools exist
        expected_tools = [
            "i686-elf-addr2line", "i686-elf-ar", "i686-elf-as",
            "i686-elf-c++filt", "i686-elf-elfedit", "i686-elf-gprof",
            "i686-elf-ld", "i686-elf-ld.bfd", "i686-elf-nm",
            "i686-elf-objcopy", "i686-elf-objdump", "i686-elf-ranlib",
            "i686-elf-readelf", "i686-elf-size", "i686-elf-strings",
            "i686-elf-strip",
        ]
        for tool in expected_tools:
            tool_path = os.path.join(bin_dir, tool)
            assert os.path.exists(tool_path), f"Missing tool: {tool}"
