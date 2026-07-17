#!/usr/bin/env python3
"""Conan test_package for farbfeld — verifies the command-line tools work.

Tests:
  1. Build test_farbfeld helper (CMake) to generate a minimal 1x1 farbfeld image
  2. Pipe it to ff2ppm (farbfeld → PPM conversion)
  3. Verify the PPM output has correct header and pixel data
  4. Also test ff2pam (farbfeld → PAM, no external deps)
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FarbfeldTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Use the compiled test_farbfeld helper to generate a farbfeld image
        test_farbfeld = os.path.join(self.build_folder, "test_farbfeld")
        ff_input = os.path.join(self.build_folder, "test.ff")
        self.run(f"{test_farbfeld} > {ff_input}")

        # Run ff2ppm to convert farbfeld → PPM
        ppm_output = os.path.join(self.build_folder, "test.ppm")
        self.run(f"ff2ppm < {ff_input} > {ppm_output}", env="conanrun")

        # Verify PPM output
        with open(ppm_output, "rb") as f:
            ppm_data = f.read()

        # PPM P6 format: "P6\n1 1\n255\n" + 3 bytes RGB pixel data
        assert ppm_data[:3] == b"P6\n", f"Expected PPM magic 'P6\\n', got {ppm_data[:3]}"
        assert b"1 1\n" in ppm_data[:15], "Expected dimensions '1 1' in PPM header"
        assert b"255\n" in ppm_data[:20], "Expected max value '255' in PPM header"
        pixel_start = ppm_data.rfind(b"255\n") + 4
        pixel_data = ppm_data[pixel_start:]
        assert len(pixel_data) == 3, f"Expected 3 bytes of pixel data, got {len(pixel_data)}"

        # Also test ff2pam (farbfeld → PAM, no external deps)
        pam_output = os.path.join(self.build_folder, "test.pam")
        self.run(f"ff2pam < {ff_input} > {pam_output}", env="conanrun")

        with open(pam_output, "rb") as f:
            pam_data = f.read()

        # PAM format: "P7\n..." header lines + pixel data
        assert pam_data[:3] == b"P7\n", f"Expected PAM magic 'P7\\n', got {pam_data[:3]}"
        assert b"WIDTH 1\n" in pam_data[:50], "Expected WIDTH 1 in PAM header"
        assert b"HEIGHT 1\n" in pam_data[:50], "Expected HEIGHT 1 in PAM header"
        assert b"DEPTH 4\n" in pam_data[:100], "Expected DEPTH 4 (RGBA) in PAM header"

        self.output.info("farbfeld test PASSED: ff2ppm and ff2pam produce correct output")
