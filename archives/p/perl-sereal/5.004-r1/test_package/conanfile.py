#!/usr/bin/env python3
"""Conan test_package for perl-sereal (Sereal front-end module).

This is the L1 test. CI runs it automatically via `conan create`.
Tests that the Sereal module and its XS dependencies are properly packaged.

Note: Runtime .so loading from Conan cache is blocked on OHOS (E046: SELinux
prevents dlopen of .so in cache directory). This test uses file-based
verification instead of runtime XS loading, following the same pattern as
perl-sereal-encoder and perl-sereal-decoder test packages.
"""
import os
import glob

from conan import ConanFile


class PerlSerealTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        sereal = self.dependencies["perl-sereal"]
        encoder = self.dependencies["perl-sereal-encoder"]
        decoder = self.dependencies["perl-sereal-decoder"]

        sereal_pm = os.path.join(sereal.package_folder, "lib", "Sereal.pm")

        # Run shell test script with package paths as arguments
        # test.sh verifies: Sereal.pm existence + content + Encoder/Decoder deps + ELF format
        test_script = os.path.join(self.recipe_folder, "test.sh")
        self.run(
            f'bash "{test_script}" "{sereal_pm}" '
            f'"{encoder.package_folder}" "{decoder.package_folder}"',
            env="conanrun",
        )

        # Additional Python-level verification for critical assertions
        if not os.path.isfile(sereal_pm):
            raise AssertionError(f"Sereal.pm not found at {sereal_pm}")
        self.output.info(f"Sereal.pm found at {sereal_pm}")

        # Verify Encoder dependency has .pm and .so
        encoder_pms = glob.glob(
            os.path.join(encoder.package_folder, "**", "Encoder.pm"), recursive=True
        )
        encoder_sos = glob.glob(
            os.path.join(encoder.package_folder, "**", "Encoder.so"), recursive=True
        )
        if not encoder_pms:
            raise AssertionError("Sereal::Encoder.pm not found in encoder package")
        if not encoder_sos:
            raise AssertionError("Encoder.so not found in encoder package")
        self.output.info(f"Sereal::Encoder.pm found at {encoder_pms[0]}")
        self.output.info(f"Encoder.so found at {encoder_sos[0]}")

        # Verify Decoder dependency has .pm and .so
        decoder_pms = glob.glob(
            os.path.join(decoder.package_folder, "**", "Decoder.pm"), recursive=True
        )
        decoder_sos = glob.glob(
            os.path.join(decoder.package_folder, "**", "Decoder.so"), recursive=True
        )
        if not decoder_pms:
            raise AssertionError("Sereal::Decoder.pm not found in decoder package")
        if not decoder_sos:
            raise AssertionError("Decoder.so not found in decoder package")
        self.output.info(f"Sereal::Decoder.pm found at {decoder_pms[0]}")
        self.output.info(f"Decoder.so found at {decoder_sos[0]}")

        # Verify Sereal.pm content references Encoder and Decoder
        with open(sereal_pm, "r") as f:
            content = f.read()
            if "package Sereal" not in content:
                raise AssertionError("Sereal.pm does not contain 'package Sereal'")
            if "use Sereal::Encoder" not in content:
                raise AssertionError("Sereal.pm does not use Sereal::Encoder")
            if "use Sereal::Decoder" not in content:
                raise AssertionError("Sereal.pm does not use Sereal::Decoder")
        self.output.info("Sereal.pm content validation passed")
