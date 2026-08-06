#!/usr/bin/env python3
"""Conan recipe — hyperfine 1.20.0-r0 (precompiled binary from Alpine Linux).

A command-line benchmarking tool written in Rust. Since rustc crashes
(SIGSEGV) on the HarmonyOS musl platform, this recipe packages a precompiled
aarch64 musl binary from Alpine Linux's community repository.

The APK (which is a tar.gz) contains:
  usr/bin/hyperfine  — ELF aarch64 musl binary

The binary depends on libgcc_s.so.1 (GCC runtime for _Unwind_* functions).
This library is bundled in lib/ since HarmonyOS doesn't provide it by default.

R32: settings.os must check in ("Linux", "OHOS").
R38: Command-line tool — commands.json declared at software level.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


HNP_BIN = "/data/service/hnp/bin"


def _sign_elf(filepath):
    """Sign an ELF binary for HarmonyOS execution (self-signed)."""
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
        import time; time.sleep(1)

    if os.path.exists(tmp):
        os.unlink(tmp)
    return False


def _set_rpath(filepath, rpath):
    """Set RPATH/RUNPATH on an ELF binary using patchelf."""
    patchelf = shutil.which("patchelf")
    if not patchelf:
        return False
    try:
        subprocess.run([patchelf, "--set-rpath", rpath, filepath],
                       capture_output=True, timeout=10)
        return True
    except Exception:
        return False


class HyperfineConan(ConanFile):
    name = "hyperfine"
    version = "1.20.0-r0"
    description = "A command-line benchmarking tool"
    license = "MIT OR Apache-2.0"
    homepage = "https://github.com/sharkdp/hyperfine"
    url = ""  # CI fills this

    package_type = "application"

    # Precompiled binary — only depends on os and arch
    settings = "os", "arch"

    # Export the man page and bundled libgcc_s.so.1
    exports = "res/hyperfine.1", "res/libgcc_s.so.1"

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
        # Precompiled binary — no compilation step needed

    def package(self):
        # Copy the precompiled binary from the extracted APK
        bin_dst = os.path.join(self.package_folder, "bin")
        copy(self, "hyperfine",
             src=os.path.join(self.source_folder, "usr", "bin"),
             dst=bin_dst)

        # Copy bundled libgcc_s.so.1 (GCC runtime for _Unwind_* functions)
        copy(self, "libgcc_s.so.1",
             src=os.path.join(self.recipe_folder, "res"),
             dst=os.path.join(self.package_folder, "lib"))

        # Set RPATH so binary can find libgcc_s.so.1 at $ORIGIN/../lib
        hyperfine_bin = os.path.join(bin_dst, "hyperfine")
        if os.path.exists(hyperfine_bin):
            _set_rpath(hyperfine_bin, "$ORIGIN/../lib")
            # Sign the ELF binary for HarmonyOS execution
            _sign_elf(hyperfine_bin)

        # Copy the man page from the recipe exports
        copy(self, "hyperfine.1",
             src=os.path.join(self.recipe_folder, "res"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.resdirs = ["share"]
        # Declare system library dependency
        self.cpp_info.system_libs = ["c"]
