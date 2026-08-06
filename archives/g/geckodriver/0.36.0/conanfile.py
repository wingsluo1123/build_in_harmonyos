#!/usr/bin/env python3
"""Conan 2.x recipe — geckodriver 0.36.0 (Mozilla WebDriver for Firefox)

geckodriver is a Rust binary that implements the WebDriver protocol
to control Gecko-based browsers (Firefox). It is built with Cargo.

Build: cargo build --release
Output: target/release/geckodriver (ELF binary)
"""
import os
import shutil
import glob

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GeckodriverConan(ConanFile):
    name = "geckodriver"
    version = "0.36.0"
    description = "Mozilla WebDriver proxy for Gecko-based browsers (Firefox)"
    license = "MPL-2.0"
    homepage = "https://github.com/mozilla/geckodriver"
    url = "https://cnb.cool/OpenHarmonyPCDeveloper/build_in_harmonyos/-/tree/main/archives/g/geckodriver"

    package_type = "application"  # CLI tool, not a library

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Rust crate dependencies are managed by Cargo via Cargo.lock, not Conan.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Ensure Rust toolchain is available on the build machine.
        # On HarmonyOS, Rust is installed via Harmonybrew (not pre-installed).
        if not shutil.which("cargo"):
            self.output.info("cargo not found, installing Rust toolchain via Harmonybrew...")
            brew_bin = os.path.join(os.path.expanduser("~"), ".harmonybrew", "bin", "brew")
            if not os.path.exists(brew_bin):
                self.run('zsh -c "$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)"')
            self.run(f'eval "$({brew_bin} shellenv)" && brew install rust')
            # Ensure cargo is in PATH for subsequent commands
            cargo_dir = os.path.join(os.path.expanduser("~"), ".harmonybrew", "bin")
            current_path = os.environ.get("PATH", "")
            os.environ["PATH"] = f"{cargo_dir}:{current_path}"

        # Ensure cc linker is available (cargo's build scripts look for 'cc')
        if not shutil.which("cc"):
            clang = shutil.which("clang")
            if clang:
                os.environ["CC"] = clang
            clangxx = shutil.which("clang++")
            if clangxx:
                os.environ["CXX"] = clangxx

        # Configure cargo sparse registry for faster downloads
        cargo_home = os.path.join(os.path.expanduser("~"), ".cargo")
        os.makedirs(cargo_home, exist_ok=True)
        config_path = os.path.join(cargo_home, "config.toml")
        if not os.path.exists(config_path):
            with open(config_path, "w") as f:
                f.write('[registries.crates-io]\nprotocol = "sparse"\n')

        # Cargo manages its own dependencies and toolchain.
        # The binary is a standalone ELF executable (no shared lib deps).
        # Explicitly set CC/CXX for cargo's build scripts (cc crate).
        clang = shutil.which("clang") or "/data/service/hnp/bin/clang"
        clangxx = shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        self.run(f"CC={clang} CXX={clangxx} cargo build --release")

    def package(self):
        # Cargo creates target/release/ relative to the build directory.
        # With basic_layout(), conan may create a build-type subdirectory,
        # so we search for the binary in the build folder and its parent.
        search_dirs = [
            os.path.join(self.build_folder, "target", "release"),
            os.path.join(os.path.dirname(self.build_folder), "target", "release"),
        ]
        for target_dir in search_dirs:
            if os.path.isfile(os.path.join(target_dir, "geckodriver")):
                copy(self, "geckodriver", target_dir, os.path.join(self.package_folder, "bin"))
                return
        # Fallback: recursive glob search
        pattern = os.path.join(os.path.dirname(self.build_folder), "**", "target", "release", "geckodriver")
        matches = glob.glob(pattern, recursive=True)
        if matches:
            copy(self, "geckodriver", os.path.dirname(matches[0]), os.path.join(self.package_folder, "bin"))
        else:
            raise ConanException("geckodriver binary not found — cargo build may have failed or output path mismatch")

    def package_info(self):
        # CLI tool: expose bin directory, not libs
        self.cpp_info.bindirs = ["bin"]
