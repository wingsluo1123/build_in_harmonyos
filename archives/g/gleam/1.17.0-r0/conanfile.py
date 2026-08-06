#!/usr/bin/env python3
"""Conan recipe for gleam — statically-typed language for the Erlang VM.

Gleam is a Rust project built with Cargo. This recipe:
1. Downloads source from GitHub (v1.17.0)
2. Applies patches to use ring crypto provider (avoids aws-lc-rs assembly issues on OHOS)
3. Installs Rust toolchain via Harmonybrew if not available
4. Builds with cargo build --release --bin gleam
5. Packages the gleam binary

Build dependencies: Rust toolchain (rustc/cargo, auto-installed via Harmonybrew), clang (for C linking)
Runtime: musl libc (system-provided on HarmonyOS)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GleamConan(ConanFile):
    name = "gleam"
    version = "1.17.0-r0"
    description = "Statically-typed language for the Erlang VM"
    license = "Apache-2.0"
    homepage = "https://gleam.run/"
    url = "https://github.com/gleam-lang/gleam"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: settings.os must be Linux or OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler paths from Conan profile conf, not bare env vars
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compiler_executables.get("c", "clang")
        cxx = compiler_executables.get("cpp", "clang++")

        # Configure cargo to use rsproxy mirror (China crates.io mirror)
        cargo_config = """[source.crates-io]
replace-with = "rsproxy-sparse"

[source.rsproxy-sparse]
registry = "sparse+https://rsproxy.cn/index/"

[net]
git-fetch-with-cli = true
retry = 5

[target.aarch64-unknown-linux-ohos]
linker = "%s"
""" % cc

        # Write cargo config to project-local .cargo directory
        cargo_dir = os.path.join(self.source_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        with open(os.path.join(cargo_dir, "config.toml"), "w") as f:
            f.write(cargo_config)

        # Ensure Rust toolchain is available (install via Harmonybrew if missing)
        brew_prefix = os.path.expanduser("~/.harmonybrew")
        cargo_bin = os.path.join(brew_prefix, "bin", "cargo")
        if not shutil.which("cargo") and not os.path.exists(cargo_bin):
            self.output.info("Rust toolchain not found, installing via Harmonybrew...")
            self.run(
                'zsh -c "$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)" && '
                f'eval "$({brew_prefix}/bin/brew shellenv)" && '
                f'{brew_prefix}/bin/brew install rust'
            )

        # Build with cargo — set CC/CXX/AR explicitly (R33)
        # Use a single shell command to ensure environment is consistent
        build_cmd = (
            f'export CC="{cc}" && '
            f'export CXX="{cxx}" && '
            f'export AR="ar" && '
            f'export CARGO_NET_RETRY=5 && '
            f'if [ -f {brew_prefix}/bin/brew ]; then '
            f'  eval "$({brew_prefix}/bin/brew shellenv)"; '
            f'fi && '
            f'cargo build --release --bin gleam'
        )
        self.run(build_cmd)

    def package(self):
        # Copy the built binary
        copy(self, "gleam",
             os.path.join(self.source_folder, "target", "release"),
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
