#!/usr/bin/env python3
"""Conan recipe for fd 10.2.0 — pre-built musl binary approach.

fd is a Rust project (GitHub: sharkdp/fd). On OHOS, rustc 1.87.0 segfaults
(SIGSEGV), so source compilation is impossible. This recipe downloads the
pre-compiled aarch64-unknown-linux-musl binary from GitHub releases and
packages it with a custom ELF loader (fd_loader) for OHOS compatibility.

Key difference from the `just` recipe: fd has a large TLS segment (2712 bytes
of .tdata), which requires the AT_PHENT auxiliary vector entry to be set
correctly. The standard elfldr does not set AT_PHENT, causing musl's TLS
initialization to fail with SIGSEGV. fd_loader is a custom ELF loader that
includes the AT_PHENT fix.
"""
import os
import stat
import shutil
import tarfile

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, download, check_sha256
from conan.tools.layout import basic_layout


class FdConan(ConanFile):
    name = "fd"
    version = "10.2.0"
    description = "fd is a simple, fast and user-friendly alternative to find"
    license = "MIT"
    homepage = "https://github.com/sharkdp/fd"
    url = ""

    settings = "os", "arch"

    # Pre-compiled binary URL (aarch64 musl static)
    _binary_url = "https://ghfast.top/https://github.com/sharkdp/fd/releases/download/v10.2.0/fd-v10.2.0-aarch64-unknown-linux-musl.tar.gz"
    _binary_sha256 = "4e8e596646d047d904f2c5ca74b39dccc69978b6e1fb101094e534b0b59c1bb0"

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
        tarball = os.path.join(self.build_folder, "fd-musl.tar.gz")
        download(self, self._binary_url, tarball, sha256=self._binary_sha256)
        # Extract (fd binary is inside fd-v10.2.0-aarch64-unknown-linux-musl/fd)
        with tarfile.open(tarball, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name.endswith("/fd") and member.isfile():
                    member.name = "fd"
                    tar.extract(member, self.build_folder)
                    break

    def package(self):
        # Install the fd binary
        copy(self, "fd", self.build_folder, os.path.join(self.package_folder, "bin"))
        # Install fd_loader (custom ELF loader with AT_PHENT fix)
        # fd_loader is built from source and provided alongside
        loader_src = os.path.join(os.path.dirname(__file__), "..", "..", "..", "bin", "fd_loader")
        if not os.path.exists(loader_src):
            # Try alternate path
            loader_src = "/storage/Users/currentUser/usr/local/bin/fd_loader"
        if os.path.exists(loader_src):
            copy(self, "fd_loader", os.path.dirname(loader_src),
                 os.path.join(self.package_folder, "bin"))
        # Create wrapper script
        wrapper_path = os.path.join(self.package_folder, "bin", "fd-wrapper")
        wrapper_content = """#!/bin/sh
# Wrapper for fd pre-built musl binary on OHOS
# Uses fd_loader (custom ELF loader with AT_PHENT fix) instead of elfldr
# because fd has a large TLS segment that requires AT_PHENT to be set
exec fd_loader "$(dirname "$0")/fd" "$@"
"""
        with open(wrapper_path, "w") as f:
            f.write(wrapper_content)
        os.chmod(wrapper_path, 0o755)

    def package_info(self):
        # fd is a standalone command-line tool, not a library
        self.cpp_info.libs = []
        # Add bin to PATH
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
