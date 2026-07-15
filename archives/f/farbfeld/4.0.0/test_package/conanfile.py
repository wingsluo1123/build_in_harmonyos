#!/usr/bin/env python3
"""Conan test_package for farbfeld — verifies the command-line tools work.

Tests:
  1. Generate a minimal 1x1 farbfeld image
  2. Pipe it to ff2ppm (farbfeld → PPM conversion)
  3. Verify the PPM output has correct header and pixel data
  4. Also test ff2pam (farbfeld → PAM, no external deps)
"""
import os
import struct

from conan import ConanFile


class FarbfeldTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Generate a minimal 1x1 farbfeld image:
        # magic "farbfeld" (8 bytes) + width (4B BE) + height (4B BE) + pixel (8B RGBA 16-bit)
        farbfeld_data = b"farbfeld"
        farbfeld_data += struct.pack(">II", 1, 1)  # width=1, height=1
        # Pixel: R=0, G=0, B=0, A=65535 (each 2 bytes big-endian)
        farbfeld_data += struct.pack(">HHHH", 0, 0, 0, 65535)

        # Write to temp file
        ff_input = os.path.join(self.build_folder, "test.ff")
        with open(ff_input, "wb") as f:
            f.write(farbfeld_data)

        # Run ff2ppm to convert farbfeld → PPM (uses conanrun env for PATH/LD_LIBRARY_PATH)
        ppm_output = os.path.join(self.build_folder, "test.ppm")
        self.run(f"ff2ppm < {ff_input} > {ppm_output}", env="conanrun")

        # Verify PPM output
        with open(ppm_output, "rb") as f:
            ppm_data = f.read()

        # PPM P6 format: "P6\n1 1\n255\n" + 3 bytes RGB pixel data
        assert ppm_data[:3] == b"P6\n", f"Expected PPM magic 'P6\\n', got {ppm_data[:3]}"
        assert b"1 1\n" in ppm_data[:15], "Expected dimensions '1 1' in PPM header"
        assert b"255\n" in ppm_data[:20], "Expected max value '255' in PPM header"
        # Pixel data should be 3 bytes (RGB for P6 format)
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
