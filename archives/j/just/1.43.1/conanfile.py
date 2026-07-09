#!/usr/bin/env python3
"""Conan recipe for just 1.43.1 — pre-built musl binary approach.

just is a Rust project. On OHOS, rustc 1.87.0 segfaults (SIGSEGV),
so source compilation is impossible. This recipe downloads the
pre-compiled aarch64-unknown-linux-musl binary from GitHub releases
and packages it with an elfldr wrapper for OHOS compatibility.

The musl static binary runs via elfldr (a custom ELF loader compiled
with clang for OHOS signature compatibility).
"""
import os
import stat
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, download, check_sha256
from conan.tools.layout import basic_layout


class JustConan(ConanFile):
    name = "just"
    version = "1.43.1"
    description = "Just a command runner - a handy way to save and run project-specific commands"
    license = "MIT"
    homepage = "https://github.com/casey/just"
    url = ""

    settings = "os", "arch"

    # Pre-compiled binary URL (aarch64 musl static)
    _binary_url = "https://ghfast.top/https://github.com/casey/just/releases/download/1.43.1/just-1.43.1-aarch64-unknown-linux-musl.tar.gz"
    _binary_sha256 = "e28e1f18cecd45d35f9fb39ef3651dd79c0623cb29a2f375ea7a1a185ac32dc9"

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
        tarball = os.path.join(self.build_folder, "just-musl.tar.gz")
        download(self, self._binary_url, tarball, sha256=self._binary_sha256)
        # Extract
        import tarfile
        with tarfile.open(tarball, "r:gz") as tar:
            tar.extract("just", self.build_folder)

    def package(self):
        # Install the binary
        copy(self, "just", self.build_folder, os.path.join(self.package_folder, "bin"))
        # Create wrapper script for elfldr compatibility on OHOS
        wrapper_path = os.path.join(self.package_folder, "bin", "just-wrapper")
        wrapper_content = '''#!/bin/sh
# Wrapper for just pre-built musl binary on OHOS
# Uses elfldr to load the static musl binary with OHOS-compatible signature
exec elfldr "$(dirname "$0")/just" "$@"
'''
        with open(wrapper_path, "w") as f:
            f.write(wrapper_content)
        os.chmod(wrapper_path, 0o755)

    def package_info(self):
        # just is a standalone command-line tool, not a library
        self.cpp_info.libs = []
        # Add bin to PATH
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
