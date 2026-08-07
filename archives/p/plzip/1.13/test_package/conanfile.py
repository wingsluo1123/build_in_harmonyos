#!/usr/bin/env python3
"""Conan test_package for plzip - runs the plzip binary to verify compression/decompression."""
import os

from conan import ConanFile


class PlzipTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test 1: Check version
        self.run("plzip --version", env="conanrun")

        # Test 2: Compress and decompress round-trip
        test_file = os.path.join(self.source_folder, "test_data.txt")
        with open(test_file, "w") as f:
            f.write("Hello, plzip! This is a test for parallel LZMA compression.\n" * 100)

        # Compress
        self.run(f"plzip {test_file}", env="conanrun")
        compressed = test_file + ".lz"
        assert os.path.exists(compressed), f"Compressed file not created: {compressed}"

        # Decompress
        self.run(f"plzip -d {compressed}", env="conanrun")
        assert os.path.exists(test_file), f"Decompressed file not restored: {test_file}"

        # Verify content
        with open(test_file, "r") as f:
            content = f.read()
        expected = "Hello, plzip! This is a test for parallel LZMA compression.\n" * 100
        assert content == expected, "Decompressed content does not match original"

        print("PASS: plzip compress/decompress round-trip OK")
