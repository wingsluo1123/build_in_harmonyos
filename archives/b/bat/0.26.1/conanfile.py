#!/usr/bin/env python3
"""Conan recipe for bat 0.26.1 — pre-built musl binary approach.

bat is a Rust project (GitHub: sharkdp/bat). On OHOS, rustc 1.87.0 segfaults
(SIGSEGV), so source compilation is impossible. This recipe downloads the
pre-compiled aarch64-unknown-linux-musl binary from GitHub releases and
packages it with a custom ELF loader (fd_loader) for OHOS compatibility.

Key finding: bat's --version works with elfldr, but all file reading/stdin
processing crashes with SIGSEGV. This is because bat requires properly
initialized TLS (AT_PHENT auxiliary vector) for complex operations like
syntax highlighting and file I/O. The fd_loader (same as used for fd)
includes the AT_PHENT fix and resolves this issue.
"""
import os
import stat
import shutil
import tarfile

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, download, check_sha256
from conan.tools.layout import basic_layout


class BatConan(ConanFile):
    name = "bat"
    version = "0.26.1"
    description = "A cat(1) clone with syntax highlighting and Git integration"
    license = "MIT"
    homepage = "https://github.com/sharkdp/bat"
    url = ""

    settings = "os", "arch"

    # Pre-compiled binary URL (aarch64 musl static)
    _binary_url = "https://ghfast.top/https://github.com/sharkdp/bat/releases/download/v0.26.1/bat-v0.26.1-aarch64-unknown-linux-musl.tar.gz"
    _binary_sha256 = "6369242c584065f195fb20cb36fbd7cb63ae690605bbe89868a7596b596c2c23"

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
        tarball = os.path.join(self.build_folder, "bat-musl.tar.gz")
        download(self, self._binary_url, tarball, sha256=self._binary_sha256)
        # Extract (bat binary is inside bat-v0.26.1-aarch64-unknown-linux-musl/bat)
        with tarfile.open(tarball, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name.endswith("/bat") and member.isfile():
                    member.name = "bat"
                    tar.extract(member, self.build_folder)
                    break

    def package(self):
        # Install the bat binary
        copy(self, "bat", self.build_folder, os.path.join(self.package_folder, "bin"))
        # Install fd_loader (custom ELF loader with AT_PHENT fix)
        # fd_loader is the same loader used for fd (also by sharkdp)
        loader_src = os.path.join(os.path.dirname(__file__), "..", "..", "..", "bin", "fd_loader")
        if not os.path.exists(loader_src):
            # Try alternate path
            loader_src = "/storage/Users/currentUser/usr/local/bin/fd_loader"
        if os.path.exists(loader_src):
            copy(self, "fd_loader", os.path.dirname(loader_src),
                 os.path.join(self.package_folder, "bin"))
        # Create wrapper script
        wrapper_path = os.path.join(self.package_folder, "bin", "bat-wrapper")
        wrapper_content = """#!/bin/sh
# Wrapper for bat pre-built musl binary on OHOS
# Uses fd_loader (custom ELF loader with AT_PHENT fix) instead of elfldr
# because bat requires properly initialized TLS for file I/O and
# syntax highlighting operations (elfldr only works for --version/--help)
exec fd_loader "$(dirname "$0")/bat" "$@"
"""
        with open(wrapper_path, "w") as f:
            f.write(wrapper_content)
        os.chmod(wrapper_path, 0o755)

    def package_info(self):
        # bat is a standalone command-line tool, not a library
        self.cpp_info.libs = []
        # Add bin to PATH
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
