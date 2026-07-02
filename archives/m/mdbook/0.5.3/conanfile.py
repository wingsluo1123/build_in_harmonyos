#!/usr/bin/env python3
"""Conan recipe — mdBook v0.5.3 (Rust/Cargo project).

mdBook is a Rust command-line tool for creating books with Markdown.
It is built with `cargo build --release --target <target>`.
Cargo manages all Rust dependencies internally; no Conan-level requires needed.
"""
import os
import shutil
import subprocess
import hashlib

from conan import ConanFile, conan_version
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, unzip
from conan.tools.layout import basic_layout


class MdbookConan(ConanFile):
    name = "mdbook"
    version = "0.5.3"
    description = "Create book from markdown files. Like Gitbook but implemented in Rust"
    license = "MPL-2.0"
    homepage = "https://github.com/rust-lang/mdBook"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def _verify_sha256(self, filepath, expected_sha256):
        """Verify SHA256 of a file."""
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        actual = h.hexdigest()
        if actual != expected_sha256:
            raise Exception(f"SHA256 mismatch: expected {expected_sha256}, got {actual}")

    def source(self):
        url = self.conan_data["sources"]["url"]
        expected_sha256 = self.conan_data["sources"].get("sha256", "")

        # Try normal Conan download first (works in CI with network access)
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
            return
        except Exception as e:
            self.output.warning(f"Normal download failed: {e}")

        # Fallback 1: check for pre-downloaded archive in standard build locations
        home = os.environ.get("HOME", "")
        tmpdir = os.environ.get("TMPDIR", "")
        candidate_paths = [
            os.path.join(home, "tmp", "builds", "mdbook-0.5.3.tar.gz"),
            os.path.join(tmpdir, "builds", "mdbook-0.5.3.tar.gz"),
        ]
        for local_path in candidate_paths:
            if os.path.exists(local_path):
                self.output.info(f"Using pre-downloaded archive: {local_path}")
                if expected_sha256:
                    self._verify_sha256(local_path, expected_sha256)
                unzip(self, local_path, self.source_folder, strip_root=True)
                return

        # Fallback 2: use curl to download (for environments with broken Python SSL)
        self.output.warning("Trying curl fallback download...")
        tmp_dir = os.path.join(self.source_folder, "_dl_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        archive = os.path.join(tmp_dir, "mdbook-0.5.3.tar.gz")
        subprocess.run(
            ["curl", "-L", "-k", "-s", "-o", archive, url],
            check=True
        )
        if expected_sha256:
            self._verify_sha256(archive, expected_sha256)
        unzip(self, archive, self.source_folder, strip_root=True)
        shutil.rmtree(tmp_dir, ignore_errors=True)

    def generate(self):
        # No Autotools/CMake toolchain needed for Cargo
        pass

    def build(self):
        apply_conandata_patches(self)
        rust_target = self._get_rust_target()
        # Build with Cargo
        self.run(f"cargo build --release --target {rust_target}")

    def _get_rust_target(self):
        """Determine the Rust target triple based on Conan settings (R32)."""
        target_map = {
            "aarch64": "aarch64-unknown-linux-ohos",
            "armv7": "armv7-unknown-linux-ohos",
            "x86_64": "x86_64-unknown-linux-ohos",
            "loongarch64": "loongarch64-unknown-linux-ohos",
        }
        arch_str = str(self.settings.arch)
        for key, triple in target_map.items():
            if key in arch_str:
                return triple
        return "aarch64-unknown-linux-ohos"

    def package(self):
        rust_target = self._get_rust_target()
        # cargo build creates target/ in the source folder (where Cargo.toml is)
        bin_dir = os.path.join(self.source_folder, "target", rust_target, "release")
        # Also check build_folder as fallback
        if not os.path.exists(os.path.join(bin_dir, "mdbook")):
            bin_dir = os.path.join(self.build_folder, "target", rust_target, "release")
        copy(self, "mdbook", bin_dir, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # mdbook is a command-line tool, not a library
        # Add bin to PATH
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
