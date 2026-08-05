#!/usr/bin/env python3
"""Conan recipe for cargo-binstall 1.21.1 — Precompiled binary (Rust musl static).

cargo-binstall installs Rust binaries from release assets on GitHub/other sources.
This recipe uses the upstream prebuilt aarch64-unknown-linux-musl static binary
because rustc crashes (SIGSEGV) on HarmonyOS and cannot compile from source.

The full.tgz contains three ELF binaries:
  - cargo-binstall: main installer binary
  - detect-targets: target platform detection helper
  - detect-wasi: WASI runtime detection helper

On HarmonyOS, ELF binaries require adhoc self-signing via binary-sign-tool.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class CargoBinstallConan(ConanFile):
    name = "cargo-binstall"
    version = "1.21.1"
    description = "Install Rust binaries from release assets — prebuilt musl static binary"
    license = "MPL-2.0"
    homepage = "https://github.com/cargo-bins/cargo-binstall"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        # No build folder layout needed for precompiled binary
        pass

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(f"Unsupported arch: {self.settings.arch}, only armv8 (aarch64) supported")

    def package_id(self):
        # Precompiled binary — independent of compiler and build_type
        del self.info.settings.compiler
        del self.info.settings.build_type

    def source(self):
        # Download prebuilt binary tarball (no strip_root — files are at root level)
        get(self, **self.conan_data["sources"])

    def build(self):
        # Apply patches (none for precompiled binary, but required by G1)
        apply_conandata_patches(self)
        # Precompiled binary — no compilation needed
        # On HarmonyOS, sign ELF binaries for execution
        if str(self.settings.os) == "OHOS":
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/objcopy"
            if os.path.exists(sign_tool):
                for binary in ["cargo-binstall", "detect-targets", "detect-wasi"]:
                    src = os.path.join(self.source_folder, binary)
                    signed = os.path.join(self.source_folder, f"{binary}.signed")
                    # Remove any existing .codesign section (may fail if not present)
                    try:
                        self.run(f'"{objcopy}" --remove-section .codesign "{src}"',
                                 cwd=self.source_folder)
                    except Exception:
                        pass
                    # Sign with adhoc self-sign
                    self.run(f'"{sign_tool}" sign -inFile "{src}" -outFile "{signed}" '
                             f'-selfSign 1 -keyAlias "default"',
                             cwd=self.source_folder)
                    # Replace original with signed version
                    shutil.move(signed, src)
                    # Ensure execute permission (binary-sign-tool may not set it)
                    os.chmod(src, 0o755)

    def package(self):
        # Copy binaries to bin/
        bin_dir = os.path.join(self.package_folder, "bin")
        for binary in ["cargo-binstall", "detect-targets", "detect-wasi"]:
            copy(self, binary, src=self.source_folder, dst=bin_dir)
            # Ensure execute permission
            dst_file = os.path.join(bin_dir, binary)
            if os.path.exists(dst_file):
                os.chmod(dst_file, 0o755)
        # Copy license and readme
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "cargo-binstall"))
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "cargo-binstall"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
