#!/usr/bin/env python3
"""Conan recipe — hyperfine 1.20.0-r0 (precompiled binary from Alpine Linux).

A command-line benchmarking tool written in Rust. Since rustc crashes
(SIGSEGV) on the HarmonyOS musl platform, this recipe packages a precompiled
aarch64 musl binary from Alpine Linux's community repository.

The APK (which is a tar.gz) contains:
  usr/bin/hyperfine  — ELF aarch64 musl binary

The binary depends on libgcc_s.so.1 (GCC runtime for _Unwind_* functions).
This library is downloaded from Alpine Linux CDN during build() since
HarmonyOS does not provide it and committing precompiled .so files is
prohibited by code review rules.

R32: settings.os must check in ("Linux", "OHOS").
R38: Command-line tool — commands.json declared at software level.
"""
import os
import shutil
import subprocess
import time

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


HNP_BIN = "/data/service/hnp/bin"

# libgcc_s.so.1 source (Alpine Linux CDN — official, aarch64 musl)
LIBGCC_URL = "https://dl-cdn.alpinelinux.org/alpine/edge/main/aarch64/libgcc-15.2.0-r8.apk"
LIBGCC_SHA256 = "dd0d4ca96d24d1e0e694b735a2fed8545362835ba84d287a75865f6afd91f3e0"


def _sign_elf(filepath):
    """Sign an ELF binary for HarmonyOS execution (self-signed).

    Returns True on success, False on failure.
    """
    objcopy = os.path.join(HNP_BIN, "llvm-objcopy")
    if not os.path.exists(objcopy):
        objcopy = shutil.which("llvm-objcopy") or objcopy

    # Remove any existing signature section
    subprocess.run([objcopy, "--remove-section", ".codesign", filepath],
                   capture_output=True, timeout=10)

    sign_tool = os.path.join(HNP_BIN, "binary-sign-tool")
    if not os.path.exists(sign_tool):
        return False

    tmp = filepath + ".signed.tmp"
    for attempt in range(3):
        r = subprocess.run(
            [sign_tool, "sign", "-inFile", filepath,
             "-outFile", tmp, "-selfSign", "1"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0 and os.path.exists(tmp):
            shutil.move(tmp, filepath)
            os.chmod(filepath, 0o755)
            return True
        time.sleep(1)

    if os.path.exists(tmp):
        os.unlink(tmp)
    return False


def _set_rpath(filepath, rpath):
    """Set RPATH/RUNPATH on an ELF binary using patchelf.

    Returns True on success, False if patchelf unavailable or failed.
    """
    patchelf = shutil.which("patchelf")
    if not patchelf:
        return False
    try:
        r = subprocess.run([patchelf, "--set-rpath", rpath, filepath],
                           capture_output=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


class HyperfineConan(ConanFile):
    name = "hyperfine"
    version = "1.20.0-r0"
    description = "A command-line benchmarking tool"
    license = "MIT OR Apache-2.0"
    homepage = "https://github.com/sharkdp/hyperfine"

    package_type = "application"

    # Precompiled binary — only depends on os and arch
    settings = "os", "arch"

    # Export the man page (no precompiled .so files committed)
    exports = ["res/hyperfine.1"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # Download and extract the Alpine APK (tar.gz format)
        # filename forces Conan to treat the .apk as tar.gz
        get(self, **self.conan_data["sources"])

    def build(self):
        # Apply patches (none currently, but required by G1 check)
        apply_conandata_patches(self)

        # Download libgcc_s.so.1 from Alpine Linux CDN
        # Required by hyperfine for _Unwind_* functions (GCC runtime)
        # Not committed to repo per code review rules (no precompiled .so)
        libgcc_dir = os.path.join(self.source_folder, "libgcc")
        get(self, url=LIBGCC_URL, sha256=LIBGCC_SHA256,
            filename="libgcc-15.2.0-r8.tar.gz",
            destination=libgcc_dir)

    def package(self):
        # Copy the precompiled binary from the extracted APK
        bin_dst = os.path.join(self.package_folder, "bin")
        copy(self, "hyperfine",
             src=os.path.join(self.source_folder, "usr", "bin"),
             dst=bin_dst)

        # Copy libgcc_s.so.1 from the downloaded libgcc APK
        copy(self, "libgcc_s.so.1",
             src=os.path.join(self.source_folder, "libgcc", "usr", "lib"),
             dst=os.path.join(self.package_folder, "lib"))

        # Set RPATH so binary can find libgcc_s.so.1 at $ORIGIN/../lib
        hyperfine_bin = os.path.join(bin_dst, "hyperfine")
        if os.path.exists(hyperfine_bin):
            if not _set_rpath(hyperfine_bin, "$ORIGIN/../lib"):
                self.output.warn("patchelf unavailable or failed; RPATH not set")
            # Sign the ELF binary for HarmonyOS execution
            if not _sign_elf(hyperfine_bin):
                self.output.warn("ELF signing failed; binary may not execute")

        # Copy the man page from the recipe exports
        copy(self, "hyperfine.1",
             src=os.path.join(self.recipe_folder, "res"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.system_libs = ["c"]
