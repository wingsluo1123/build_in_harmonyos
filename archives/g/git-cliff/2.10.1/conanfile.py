#!/usr/bin/env python3
"""Conan recipe — git-cliff 2.10.1

A highly customizable changelog generator for Rust projects.
Cargo/Rust workspace project. Builds a single binary: git-cliff.
License: MIT OR Apache-2.0
Homepage: https://github.com/orhun/git-cliff
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.errors import ConanException

# Rust bottle URL (Harmonybrew, OHOS-native build)
RUST_BOTTLE_URL = "https://harmonybrew.atomgit.com/bottles/rust-1.97.1.arm64_ohos.bottle.tar.gz"

# Cargo mirror config (crates.io is unreachable on OHOS network)
CARGO_CONFIG = """[source.crates-io]
replace-with = 'rsproxy-sparse'

[source.rsproxy-sparse]
registry = "sparse+https://rsproxy.cn/index/"

[net]
git-fetch-with-cli = true
"""


class GitCliffConan(ConanFile):
    name = "git-cliff"
    version = "2.10.1"
    description = "A highly customizable changelog generator — see your git history in style"
    license = "MIT OR Apache-2.0"
    homepage = "https://github.com/orhun/git-cliff"
    url = "https://github.com/orhun/git-cliff"

    package_type = "application"

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

    def _ensure_rust(self):
        """Find or install Rust toolchain. Returns (cargo_path, env_dict)."""
        env = {}

        # 1. Try to find existing cargo
        cargo = shutil.which("cargo")
        if cargo:
            return cargo, env

        # 2. Check common installation locations
        for candidate in [
            os.path.expanduser("~/.harmonybrew/bin/cargo"),
            "/storage/Users/currentUser/.harmonybrew/bin/cargo",
            "/storage/Users/currentUser/usr/local/bin/cargo",
        ]:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate, env

        # 3. Download and install Rust bottle locally
        rust_dir = os.path.join(self.build_folder, ".rust-toolchain")
        cargo_path = os.path.join(rust_dir, "bin", "cargo")
        rustc_path = os.path.join(rust_dir, "bin", "rustc")

        if not os.path.isfile(cargo_path):
            self.output.info("Rust toolchain not found, downloading from Harmonybrew...")
            bottle_path = os.path.join(self.build_folder, ".rust-bottle.tar.gz")
            self.run(f'curl -fsSL -o "{bottle_path}" "{RUST_BOTTLE_URL}"')
            os.makedirs(rust_dir, exist_ok=True)
            # Bottle structure: rust/1.97.1/bin/cargo -> strip 2 levels
            self.run(f'tar xzf "{bottle_path}" -C "{rust_dir}" --strip-components=2')
            # Make binaries executable
            for name in ["cargo", "rustc", "rustfmt", "clippy-driver"]:
                p = os.path.join(rust_dir, "bin", name)
                if os.path.isfile(p):
                    os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)

        if not os.path.isfile(cargo_path):
            raise ConanException("Failed to install Rust toolchain from Harmonybrew bottle")

        # Set up PATH so cargo can find rustc
        env["PATH"] = os.path.join(rust_dir, "bin") + ":" + os.environ.get("PATH", "")

        return cargo_path, env

    def _ensure_cc(self):
        """Ensure cc/c++ symlinks exist (cargo uses 'cc' as default linker)."""
        if shutil.which("cc"):
            return

        clang = shutil.which("clang") or "/data/service/hnp/bin/clang"
        clangxx = shutil.which("clang++") or "/data/service/hnp/bin/clang++"

        local_bin = os.path.join(self.build_folder, ".local-bin")
        os.makedirs(local_bin, exist_ok=True)

        cc_link = os.path.join(local_bin, "cc")
        cxx_link = os.path.join(local_bin, "c++")
        if not os.path.exists(cc_link) and os.path.isfile(clang):
            os.symlink(clang, cc_link)
        if not os.path.exists(cxx_link) and os.path.isfile(clangxx):
            os.symlink(clangxx, cxx_link)

        return local_bin

    def _setup_cargo_mirror(self):
        """Set up CARGO_HOME with rsproxy mirror config."""
        cargo_home = os.path.join(self.build_folder, ".cargo-home")
        config_path = os.path.join(cargo_home, "config.toml")

        if not os.path.isfile(config_path):
            os.makedirs(cargo_home, exist_ok=True)
            with open(config_path, "w") as f:
                f.write(CARGO_CONFIG)

        return cargo_home

    def build(self):
        apply_conandata_patches(self)

        cargo, rust_env = self._ensure_rust()
        local_bin = self._ensure_cc()
        cargo_home = self._setup_cargo_mirror()

        # Build environment: cargo + rustc in PATH, cc/c++ available, cargo mirror configured
        build_env = dict(rust_env)
        build_env["CARGO_HOME"] = cargo_home
        if local_bin:
            existing_path = build_env.get("PATH", os.environ.get("PATH", ""))
            build_env["PATH"] = local_bin + ":" + existing_path

        # Export env vars and run cargo build
        env_str = " ".join(f'{k}="{v}"' for k, v in build_env.items())
        self.run(f'{env_str} "{cargo}" build --release')

    def package(self):
        # Copy the release binary to bin/
        target_dir = os.path.join(self.build_folder, "target", "release")
        copy(self, "git-cliff", target_dir, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
