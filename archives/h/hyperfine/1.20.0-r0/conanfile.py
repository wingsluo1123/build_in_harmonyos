#!/usr/bin/env python3
"""Conan recipe for hyperfine 1.20.0-r0 — precompiled binary from Alpine Linux.

hyperfine is a command-line benchmarking tool written in Rust.
rustc crashes (SIGSEGV) on HarmonyOS musl platform, so source compilation
is not possible. This recipe packages the precompiled aarch64 musl binary
from the official Alpine Linux community repository.

The Alpine APK is a tar.gz containing usr/bin/hyperfine (ELF 64-bit aarch64,
dynamically linked against musl libc). The binary is extracted and signed
for HarmonyOS execution.

Build approach:
  - Download Alpine APK (official Alpine CDN)
  - Extract the precompiled hyperfine binary
  - Sign the ELF for HarmonyOS execution
  - Package into bin/

R38: This is a command-line tool (produces the `hyperfine` executable),
     not a library, so a software-level commands.json is required.
"""
import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import download, copy, apply_conandata_patches, export_conandata_patches


class HyperfineConan(ConanFile):
    name = "hyperfine"
    version = "1.20.0-r0"
    description = "Command-line benchmarking tool written in Rust"
    license = "MIT"
    homepage = "https://github.com/sharkdp/hyperfine"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                f"Unsupported arch: {self.settings.arch} (only armv8/aarch64 supported)")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # Download the Alpine APK (tar.gz format, not zip despite .apk extension).
        # Conan's get() auto-detects .apk as zip, so we use download() + manual
        # tar extraction instead.
        src = self.conan_data["sources"]
        apk_path = os.path.join(self.source_folder, "hyperfine.apk")
        download(self, url=src["url"], filename=apk_path, sha256=src["sha256"])
        # Extract using tar (Alpine APK is a gzip-compressed tar archive)
        self.run(f'tar xzf "{apk_path}" -C "{self.source_folder}"')

    def build(self):
        # No compilation step — the binary is precompiled by Alpine Linux
        # using rustc with musl target. rustc crashes (SIGSEGV) on HarmonyOS
        # musl platform, so source compilation is not possible.
        # See knowledge E072: rustc SIGSEGV on musl platform.
        apply_conandata_patches(self)

    def _sign_elf(self, filepath):
        """Sign an ELF binary for HarmonyOS execution.

        HarmonyOS requires ELF binaries to be signed before they can be
        executed. Uses the system's binary-sign-tool and llvm-objcopy.
        Returns 0 on success, 3 on failure or skip.
        """
        elf_path = Path(filepath)
        if not elf_path.exists():
            return 3

        try:
            if elf_path.read_bytes()[:4] != b'\x7fELF':
                return 3
        except Exception:
            return 3

        hnp_bin = "/data/service/hnp/bin"
        objcopy = shutil.which("llvm-objcopy") or f"{hnp_bin}/llvm-objcopy"
        sign_tool = f"{hnp_bin}/binary-sign-tool"

        if not Path(sign_tool).exists():
            sign_tool = shutil.which("binary-sign-tool") or f"{hnp_bin}/binary-sign-tool"
            if not sign_tool or not Path(sign_tool).exists():
                self.output.warning("binary-sign-tool not found, skipping ELF signing")
                return 3

        # Remove old signature if present
        try:
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", str(elf_path)],
                capture_output=True, timeout=10,
            )
        except Exception:
            pass

        # Sign
        tmp = elf_path.with_suffix(elf_path.suffix + ".signed.tmp")
        for attempt in range(3):
            try:
                r = subprocess.run(
                    [sign_tool, "sign", "-inFile", str(elf_path),
                     "-outFile", str(tmp), "-selfSign", "1"],
                    capture_output=True, text=True, timeout=30,
                )
                if r.returncode == 0 and tmp.exists():
                    shutil.move(str(tmp), str(elf_path))
                    break
            except Exception:
                pass
            if attempt < 2:
                import time
                time.sleep(1)
        else:
            tmp.unlink(missing_ok=True)
            self.output.warning(f"ELF signing failed for {elf_path.name}")
            return 3

        os.chmod(elf_path, 0o755)
        self.output.info(f"ELF signed: {elf_path.name}")
        return 0

    def package(self):
        # Extract the precompiled binary from the Alpine APK source tree.
        # The APK structure is: usr/bin/hyperfine
        bin_src = os.path.join(self.source_folder, "usr", "bin", "hyperfine")
        if not os.path.isfile(bin_src):
            raise Exception(
                f"Precompiled hyperfine binary not found at {bin_src}. "
                "The Alpine APK should contain usr/bin/hyperfine."
            )

        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "hyperfine", src=os.path.dirname(bin_src), dst=bindir)

        # Sign the ELF binary for HarmonyOS execution
        self._sign_elf(os.path.join(bindir, "hyperfine"))

    def package_info(self):
        # Command-line tool: executables in bin/, no libraries
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
