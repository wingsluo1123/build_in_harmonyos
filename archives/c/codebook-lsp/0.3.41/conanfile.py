#!/usr/bin/env python3
"""Conan recipe — codebook-lsp 0.3.41 (Rust/Cargo project).

codebook-lsp is a code-aware spell checker with LSP language server implementation.
Built with cargo (Rust edition 2024), uses rustls + aws-lc-rs for TLS.

This recipe follows R26/R27/R32 rules:
- R26: No system .so pollution (binary only, no shared libs)
- R27: Dependencies use @ohpcd/stable (none needed — all vendored via cargo)
- R32: settings.os check uses `in ("Linux", "OHOS")`
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CodebookLspConan(ConanFile):
    name = "codebook-lsp"
    version = "0.3.41"
    description = "A code-aware spell checker with LSP language server implementation"
    license = "MIT"
    homepage = "https://github.com/blopker/codebook"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # All Rust dependencies are managed by cargo (Cargo.lock)
        # No conan-level dependencies needed
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os check must use `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "Only Linux/OHOS supported"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # No cmake/autotools toolchain needed for Rust
        pass

    def build(self):
        # Apply patches if any (R6)
        apply_conandata_patches(self)

        # --- Environment setup (explicit, not relying on os.environ) ---
        # R26/R32: Set explicit paths for OpenSSL and build tools
        harmonybrew = "/storage/Users/currentUser/.harmonybrew"

        env = {
            "LD_LIBRARY_PATH": f"{harmonybrew}/lib",
            "PKG_CONFIG_PATH": f"{harmonybrew}/lib/pkgconfig",
            "OPENSSL_DIR": harmonybrew,
            "OPENSSL_LIB_DIR": f"{harmonybrew}/lib",
            "OPENSSL_INCLUDE_DIR": f"{harmonybrew}/include",
            "OPENSSL_STATIC": "1",
        }
        for k, v in env.items():
            os.environ[k] = v

        # --- Apply cargo registry patches ---
        # Cargo registry patches are temporary; they must be re-applied
        # after cargo fetches dependencies but before cargo build.
        # We apply them by finding the cargo registry source directories
        # and running patch on the relevant files.
        self._apply_cargo_registry_patches()

        # Build the codebook-lsp binary
        self.run("cargo build --release --locked -p codebook-lsp", cwd=self.source_folder)

    def _apply_cargo_registry_patches(self):
        """Apply patches to cargo registry crates (nix 0.26.4, aws-lc-sys 0.41.0).

        These patches fix OHOS platform compatibility issues that cannot be
        resolved through environment variables alone. The patches are applied
        to the cargo registry source directories after `cargo fetch` has
        downloaded them but before `cargo build` compiles them.
        """
        cargo_home = os.environ.get("CARGO_HOME", os.path.expanduser("~/.cargo"))
        registry_src = os.path.join(cargo_home, "registry", "src")

        if not os.path.isdir(registry_src):
            # Registry not yet populated; cargo build will fetch first,
            # and patches will need to be applied via a build script hook.
            self.output.warning(
                "Cargo registry not found. Patches will need manual application "
                "after cargo fetch. See patches/ directory for details."
            )
            return

        patches_dir = os.path.join(self.recipe_folder, "patches")

        # Find the registry hash directory
        for entry in os.listdir(registry_src):
            reg_dir = os.path.join(registry_src, entry)

            # Patch nix 0.26.4
            nix_dir = os.path.join(reg_dir, "nix-0.26.4")
            if os.path.isdir(nix_dir):
                patch_file = os.path.join(patches_dir, "0001-nix-ohos-compat.patch")
                if os.path.isfile(patch_file):
                    self.output.info(f"Applying nix 0.26.4 OHOS compatibility patch")
                    subprocess.run(
                        ["patch", "-p1", "-d", nix_dir, "-i", patch_file],
                        check=False,  # Don't fail if already applied
                    )

            # Patch aws-lc-sys 0.41.0
            awslc_dir = os.path.join(reg_dir, "aws-lc-sys-0.41.0")
            if os.path.isdir(awslc_dir):
                patch_file = os.path.join(patches_dir, "0002-aws-lc-sys-cmake-arch.patch")
                if os.path.isfile(patch_file):
                    self.output.info(f"Applying aws-lc-sys 0.41.0 CMake arch patch")
                    subprocess.run(
                        ["patch", "-p1", "-d", awslc_dir, "-i", patch_file],
                        check=False,  # Don't fail if already applied
                    )

    def package(self):
        # Install the binary to bin/
        binary = os.path.join(self.source_folder, "target", "release", "codebook-lsp")
        copy(self, "codebook-lsp", src=os.path.dirname(binary), dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # This is a binary (executable), not a library.
        # Only set bindirs; do not set libs (R26: no .so pollution).
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
