#!/usr/bin/env python3
"""Conan recipe — sem-cli 0.16.0 (Cargo/Rust project).

sem-cli is a semantic version control CLI built with Rust/Cargo.
This recipe uses direct cargo commands since conan.tools.cargo is not available.
Both openssl and libgit2 are conan-managed dependencies.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment


class SemcliConan(ConanFile):
    name = "sem-cli"
    version = "0.16.0"
    description = "Semantic version control CLI with entity-level diffs and blame"
    license = "MIT OR Apache-2.0"
    homepage = "https://github.com/Ataraxy-Labs/sem"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # R27: dependencies must use @ohpcd/stable
    def requirements(self):
        self.requires("openssl/3.5.6@ohpcd/stable")
        self.requires("libgit2/1.9.4@ohpcd/stable")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.build = "."
        self.folders.package = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R32: settings.os must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")

        # Set up environment for cargo to find openssl and libgit2 (both conan-managed)
        openssl_info = self.dependencies["openssl"]
        openssl_root = openssl_info.package_folder

        libgit2_info = self.dependencies["libgit2"]
        libgit2_root = libgit2_info.package_folder

        env = Environment()
        # Set PKG_CONFIG_PATH so cargo can find openssl and libgit2
        pkg_config_paths = []
        if openssl_root:
            for subdir in ["lib/pkgconfig", "lib64/pkgconfig"]:
                path = os.path.join(openssl_root, subdir)
                if os.path.isdir(path):
                    pkg_config_paths.append(path)
        if libgit2_root:
            for subdir in ["lib/pkgconfig", "lib64/pkgconfig"]:
                path = os.path.join(libgit2_root, subdir)
                if os.path.isdir(path):
                    pkg_config_paths.append(path)

        if pkg_config_paths:
            existing = os.environ.get("PKG_CONFIG_PATH", "")
            all_paths = ":".join(pkg_config_paths + ([existing] if existing else []))
            env.define("PKG_CONFIG_PATH", all_paths)

        # Set OPENSSL_DIR for Rust openssl-sys crate discovery
        if openssl_root:
            env.define("OPENSSL_DIR", openssl_root)

        # Set LIBGIT2_DIR for Rust git2 crate discovery (conan-managed)
        env.define("LIBGIT2_DIR", libgit2_root)

        envvars = env.vars(self)
        envvars.save_script("conanbuild_env")

    def build(self):
        apply_conandata_patches(self)
        # Build with cargo - sem-cli uses workspace at crates/sem-cli/Cargo.toml
        # Set CARGO_TARGET_DIR to avoid conflicts with source tree
        self.run("CARGO_TARGET_DIR=target cargo build --release --manifest-path crates/sem-cli/Cargo.toml")

    def package(self):
        # Copy the built binary to package bin directory
        binary = os.path.join(self.build_folder, "target", "release", "sem")
        if not os.path.exists(binary):
            binary = os.path.join(self.build_folder, "crates", "target", "release", "sem")
        copy(self, "sem", src=os.path.dirname(binary), dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
