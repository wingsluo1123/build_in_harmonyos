#!/usr/bin/env python3
"""Conan recipe for jwt-cli 6.2.0 — Rust project (cargo build).

jwt-cli is a CLI tool written in Rust for encoding/decoding JWTs.
Uses cargo build instead of configure/make.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class JwtcliConan(ConanFile):
    name = "jwt-cli"
    version = "6.2.0"
    description = "A super fast CLI tool to decode and encode JWTs built in Rust"
    license = "MIT"
    homepage = "https://github.com/mike-engel/jwt-cli"
    url = "https://github.com/mike-engel/jwt-cli/archive/refs/tags/6.2.0.tar.gz"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: Terminal tools must be statically linked
        pass

    def build(self):
        apply_conandata_patches(self)
        # Build Rust project using cargo with OHOS target triple
        # --target aarch64-unknown-linux-ohos is required for OHOS cross-compilation
        # Separate target dir avoids OHOS auto-sign "Text file busy" race condition
        target_dir = os.path.join(self.build_folder, "target")
        self.run(
            f"cargo build --release --target aarch64-unknown-linux-ohos --target-dir={target_dir}",
            cwd=self.source_folder,
        )

    def package(self):
        # Copy the jwt binary from separate target dir
        # With --target aarch64-unknown-linux-ohos, binary is in target/<triple>/release/
        target_dir = os.path.join(self.build_folder, "target")
        triple_dir = os.path.join(target_dir, "aarch64-unknown-linux-ohos")
        copy(self, "jwt",
             src=os.path.join(triple_dir, "release"),
             dst=os.path.join(self.package_folder, "bin"))
        # Copy license
        copy(self, "LICENSE*",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # jwt-cli is a binary tool, not a library
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
