#!/usr/bin/env python3
"""Conan recipe — rubyfmt 0.14.1 (Rust/cargo project).

rubyfmt is a Ruby autoformatter written in Rust.
Build system: cargo (cargo build --release)
Binary: rubyfmt-main (renamed to rubyfmt)

Notes:
- jemalloc disabled via patch (patches/0001-Cargo.toml.patch) due to OHOS platform incompatibility
- LIBCLANG_PATH required for ruby-prism-sys (bindgen FFI), dynamically resolved via llvm-config
- LD_LIBRARY_PATH required for cargo binary to find OpenSSL
"""
import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class RubyfmtConan(ConanFile):
    name = "rubyfmt"
    version = "0.14.1"
    description = "Ruby autoformatter written in Rust"
    license = "MIT"
    homepage = "https://github.com/fables-tales/rubyfmt"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # Explicitly export patch files so they're available during build
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        # Apply patches declared in conandata.yml (0001-Cargo.toml.patch disables jemalloc)
        apply_conandata_patches(self)

        # Verify patch was applied; if not, apply manually via subprocess
        cargo_toml = Path(self.source_folder) / "Cargo.toml"
        content = cargo_toml.read_text()
        if "default-features = false" not in content:
            # Patch wasn't applied by apply_conandata_patches; apply manually
            patch_candidates = [
                os.path.join(self.source_folder, "patches", "0001-Cargo.toml.patch"),
            ]
            # Try export_sources_folder if available
            try:
                patch_candidates.append(
                    os.path.join(self.export_sources_folder, "patches", "0001-Cargo.toml.patch")
                )
                patch_candidates.append(
                    os.path.join(self.export_sources_folder, "0001-Cargo.toml.patch")
                )
            except Exception:
                pass

            patch_applied = False
            for pf in patch_candidates:
                if os.path.exists(pf):
                    subprocess.run(
                        ["patch", "-p1", "-i", pf],
                        cwd=self.source_folder,
                        check=True,
                    )
                    self.output.info(f"Applied patch: {pf}")
                    patch_applied = True
                    break

            if not patch_applied:
                # Last resort: modify Cargo.toml directly
                content = content.replace(
                    'rubyfmt = { path = "./librubyfmt" }',
                    'rubyfmt = { path = "./librubyfmt", default-features = false }'
                )
                cargo_toml.write_text(content)
                self.output.warning("Patch file not found; modified Cargo.toml directly")

        # Set environment for cargo build
        env = os.environ.copy()

        # LIBCLANG_PATH for ruby-prism-sys (bindgen) — dynamically resolve via llvm-config
        try:
            llvm_libdir = subprocess.check_output(
                ["llvm-config", "--libdir"], text=True
            ).strip()
        except Exception:
            llvm_libdir = os.path.expanduser(
                "~/.harmonybrew/Cellar/ohos-sdk/26.0.0.18_1/native/llvm/lib"
            )
        env["LIBCLANG_PATH"] = llvm_libdir

        # LD_LIBRARY_PATH for cargo binary to find OpenSSL
        brew_lib = os.path.expanduser("~/.harmonybrew/lib")
        env["LD_LIBRARY_PATH"] = brew_lib + ":" + env.get("LD_LIBRARY_PATH", "")

        # PATH for cargo/rustc
        brew_bin = os.path.expanduser("~/.harmonybrew/bin")
        env["PATH"] = brew_bin + ":" + env.get("PATH", "")

        env["CC"] = "clang"
        env["CXX"] = "clang++"

        # Run cargo build (jemalloc disabled via patch in Cargo.toml)
        cargo = os.path.join(brew_bin, "cargo")
        subprocess.run(
            [cargo, "build", "--release", "--no-default-features", "-j1"],
            cwd=self.source_folder,
            env=env,
            check=True,
        )

    def package(self):
        # Copy the binary, rename rubyfmt-main -> rubyfmt
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        src_bin = os.path.join(self.source_folder, "target", "release", "rubyfmt-main")
        dst_bin = os.path.join(bin_dir, "rubyfmt")
        shutil.copy2(src_bin, dst_bin)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
