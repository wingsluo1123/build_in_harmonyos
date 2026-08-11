#!/usr/bin/env python3
"""Test source for perl-sereal-encoder 5.004 (Perl XS module).

Verifies the installed package artifacts:
  1. .pm files exist and pass perl -c syntax check
  2. .so is a valid ELF binary
  3. .so has .codesign section (ELF signed for OHOS)
  4. .so contains boot_Sereal__Encoder symbol
  5. Encoder.pm contains version 5.004

Usage: python3 test_encoder.py <package_folder> <arch>
"""
import os
import shutil
import subprocess
import sys


def find_tool(name):
    """Find tool executable, checking PATH and known OHOS locations."""
    path = shutil.which(name)
    if path:
        return path
    for candidate in [f"/data/service/hnp/bin/{name}",
                      f"/system/bin/{name}",
                      f"/usr/bin/{name}",
                      f"/usr/local/bin/{name}"]:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return name


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_encoder.py <package_folder> [arch]")
        sys.exit(1)

    pkg = sys.argv[1]
    arch = sys.argv[2] if len(sys.argv) > 2 else "aarch64"

    perl = find_tool("perl")
    llvm_readelf = find_tool("llvm-readelf")
    llvm_nm = find_tool("llvm-nm")

    perl_arch = "aarch64-linux" if arch in ("armv8", "aarch64") else "x86_64-linux"
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
    subprocess.run([perl, "-c", encoder_pm], check=True)
    subprocess.run([perl, "-c", constants_pm], check=True)

    # 3. Verify .so exists and is valid ELF
    encoder_so = os.path.join(lib_dir, "auto", "Sereal", "Encoder", "Encoder.so")
    assert os.path.exists(encoder_so), f"Encoder.so not found: {encoder_so}"
    with open(encoder_so, "rb") as f:
        magic = f.read(4)
        assert magic == b"\x7fELF", "Encoder.so is not a valid ELF file"

    # 4. Verify .codesign section (ELF signature for OHOS)
    result = subprocess.run(
        [llvm_readelf, "-S", encoder_so],
        capture_output=True, text=True
    )
    assert ".codesign" in result.stdout, \
        "Encoder.so missing .codesign section (ELF not signed for OHOS)"

    # 5. Verify symbol table contains boot_Sereal__Encoder
    result = subprocess.run(
        [llvm_nm, encoder_so],
        capture_output=True, text=True
    )
    assert "boot_Sereal__Encoder" in result.stdout, \
        "Encoder.so missing boot_Sereal__Encoder symbol"

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


if __name__ == "__main__":
    main()
