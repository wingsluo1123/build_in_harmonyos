#!/usr/bin/env python3
"""Conan recipe for zoxide 0.9.8 — pre-built musl binary approach.

zoxide is a Rust project. On OHOS, rustc segfaults (SIGSEGV),
so source compilation is impossible. This recipe downloads the
pre-compiled aarch64-unknown-linux-musl binary from GitHub releases
and packages it with an elfldr wrapper for OHOS compatibility.

The musl static binary runs via elfldr (a custom ELF loader compiled
with clang for OHOS signature compatibility).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, download, check_sha256
from conan.tools.layout import basic_layout


class ZoxideConan(ConanFile):
    name = "zoxide"
    version = "0.9.8"
    description = "A smarter cd command. Supports your shell and all major system configurations."
    license = "MIT"
    homepage = "https://github.com/ajeetdsouza/zoxide"
    url = ""

    settings = "os", "arch"

    # Pre-compiled binary URL (aarch64 musl static)
    _binary_url = "https://ghfast.top/https://github.com/ajeetdsouza/zoxide/releases/download/v0.9.8/zoxide-0.9.8-aarch64-unknown-linux-musl.tar.gz"
    _binary_sha256 = "078cc9cc8cedb6c45edb84c0f5bad53518c610859c73bdb3009a52b89652c103"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # Download source tarball for reference (not compiled due to rustc segfault)
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches (none for pre-built binary)
        apply_conandata_patches(self)
        # Download pre-compiled musl binary
        tarball = os.path.join(self.build_folder, "zoxide-musl.tar.gz")
        download(self, self._binary_url, tarball, sha256=self._binary_sha256)
        # Extract the zoxide binary
        import tarfile
        with tarfile.open(tarball, "r:gz") as tar:
            tar.extract("zoxide", self.build_folder)

    def package(self):
        # Install the binary
        copy(self, "zoxide", self.build_folder, os.path.join(self.package_folder, "bin"))
        # Create wrapper script for elfldr compatibility on OHOS
        wrapper_path = os.path.join(self.package_folder, "bin", "zoxide-wrapper")
        wrapper_content = '''#!/bin/sh
# Wrapper for zoxide pre-built musl binary on OHOS
# Uses elfldr to load the static musl binary with OHOS-compatible signature
exec elfldr "$(dirname "$0")/zoxide" "$@"
'''
        with open(wrapper_path, "w") as f:
            f.write(wrapper_content)
        os.chmod(wrapper_path, 0o755)

    def package_info(self):
        # zoxide is a standalone command-line tool, not a library
        self.cpp_info.libs = []
        # Add bin to PATH
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
