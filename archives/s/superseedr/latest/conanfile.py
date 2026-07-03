#!/usr/bin/env python3
"""Conan recipe — superseedr (Rust/Cargo project).

Build system: Cargo (rustc)
Software: superseedr — A BitTorrent Client in your Terminal
License: GPL-3.0-or-later
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.errors import ConanInvalidConfiguration


class SuperseedrConan(ConanFile):
    name = "superseedr"
    version = "latest"
    description = "A BitTorrent Client in your Terminal"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/Jagalite/superseedr"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Find cargo binary
        cargo = shutil.which("cargo") or os.path.expanduser("~/.harmonybrew/bin/cargo")
        if not os.path.isfile(cargo):
            raise ConanInvalidConfiguration("cargo not found. Install Rust via harmonybrew: brew install rust")

        # Set environment for OpenSSL and Cargo
        os.environ["TMPDIR"] = os.environ.get("TMPDIR", os.path.expanduser("~/tmp"))
        os.environ["PKG_CONFIG_PATH"] = ":".join([
            os.path.expanduser("~/.harmonybrew/lib/pkgconfig"),
            os.path.expanduser("~/usr/local/lib/pkgconfig"),
        ])
        os.environ["OPENSSL_DIR"] = os.path.expanduser("~/usr/local")
        os.environ["OPENSSL_LIB_DIR"] = os.path.expanduser("~/usr/local/lib")
        os.environ["OPENSSL_INCLUDE_DIR"] = os.path.expanduser("~/usr/local/include")
        # Ensure harmonybrew bin is in PATH for cargo and rustc
        path = os.environ.get("PATH", "")
        brew_bin = os.path.expanduser("~/.harmonybrew/bin")
        if brew_bin not in path:
            os.environ["PATH"] = brew_bin + ":" + path

        # Build with Cargo
        self.run(f'"{cargo}" build --release', cwd=self.source_folder)

    def package(self):
        # Install the binary to bin/
        copy(self, "superseedr",
             src=os.path.join(self.source_folder, "target", "release"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
