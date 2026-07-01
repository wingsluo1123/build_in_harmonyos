#!/usr/bin/env python3
"""Conan test_package for perl-sereal-encoder 5.004 (Perl XS module).

L1 test: verify the Perl module files are present and valid.
Full verification: file existence + Perl syntax + ELF format + .codesign
signature + symbol table + module metadata.

Note: .so loading is restricted on HarmonyOS due to file permission model
(perl runs as UID 20020101, conan-built .so owned by UID 20001006, chmod
ineffective per E046). File-based verification is used instead.
"""
import os
import subprocess

from conan import ConanFile


class PerlSerealEncoderTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        dep = self.dependencies["perl-sereal-encoder"]
        pkg = dep.package_folder

        perl_arch = "aarch64-linux" if str(self.settings.arch) in ("armv8", "aarch64") else "x86_64-linux"
        perl_ver = "5.42.0"
        lib_dir = os.path.join(pkg, "data", "service", "hnp", "perl.org",
                               f"perl_{perl_ver}", "lib", "site_perl",
                               perl_ver, perl_arch)

        # 1. Verify .pm files exist
        encoder_pm = os.path.join(lib_dir, "Sereal", "Encoder.pm")
        constants_pm = os.path.join(lib_dir, "Sereal", "Encoder", "Constants.pm")
        assert os.path.exists(encoder_pm), f"Encoder.pm not found: {encoder_pm}"
        assert os.path.exists(constants_pm), f"Constants.pm not found: {constants_pm}"

        # 2. Verify .pm syntax (perl -c, does not load .so)
        self.run(f'perl -c "{encoder_pm}"')
        self.run(f'perl -c "{constants_pm}"')

        # 3. Verify .so exists and is valid ELF
        encoder_so = os.path.join(lib_dir, "auto", "Sereal", "Encoder", "Encoder.so")
        assert os.path.exists(encoder_so), f"Encoder.so not found: {encoder_so}"
        with open(encoder_so, "rb") as f:
            magic = f.read(4)
            assert magic == b"\x7fELF", f"Encoder.so is not a valid ELF file"

        # 4. Verify .codesign section (ELF signature for OHOS)
        result = subprocess.run(
            ["llvm-readelf", "-S", encoder_so],
            capture_output=True, text=True
        )
        assert ".codesign" in result.stdout, \
            f"Encoder.so missing .codesign section (ELF not signed for OHOS)"

        # 5. Verify symbol table contains boot_Sereal__Encoder
        result = subprocess.run(
            ["llvm-nm", encoder_so],
            capture_output=True, text=True
        )
        assert "boot_Sereal__Encoder" in result.stdout, \
            f"Encoder.so missing boot_Sereal__Encoder symbol"

        # 6. Verify module version metadata in Encoder.pm
        with open(encoder_pm, "r") as f:
            pm_content = f.read()
        assert "5.004" in pm_content, "Encoder.pm missing version 5.004"

        # 7. Print summary
        print(f"perl-sereal-encoder 5.004: file verification OK")
        print(f"  Encoder.pm:     {os.path.getsize(encoder_pm)} bytes")
        print(f"  Constants.pm:   {os.path.getsize(constants_pm)} bytes")
        print(f"  Encoder.so:     {os.path.getsize(encoder_so)} bytes (ELF aarch64, signed)")
        print(f"  Note: .so runtime load skipped — HarmonyOS file permission model (E046)")
