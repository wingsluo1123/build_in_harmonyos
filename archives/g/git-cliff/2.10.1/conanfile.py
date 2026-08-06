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
        """Find or install Rust toolchain. Returns (cargo_path, rustc_path, env_dict)."""
        env = {}

        # 1. Try to find existing cargo
        cargo = shutil.which("cargo")
        rustc = shutil.which("rustc")
        if cargo and rustc:
            return cargo, rustc, env

        # 2. Check common installation locations
        for base in [
            os.path.expanduser("~/.harmonybrew/bin"),
            "/storage/Users/currentUser/.harmonybrew/bin",
            "/storage/Users/currentUser/usr/local/bin",
        ]:
            c = os.path.join(base, "cargo")
            r = os.path.join(base, "rustc")
            if os.path.isfile(c) and os.access(c, os.X_OK):
                return c, r, env

        # 3. Download and install Rust bottle locally
        rust_dir = os.path.join(self.build_folder, ".rust-toolchain")
        # cargo.real is the actual binary; 'cargo' is a wrapper that hardcodes
        # the Harmonybrew Cellar path, so we use cargo.real directly.
        cargo_path = os.path.join(rust_dir, "bin", "cargo.real")
        rustc_path = os.path.join(rust_dir, "bin", "rustc")

        if not os.path.isfile(cargo_path):
            self.output.info("Rust toolchain not found, downloading from Harmonybrew...")
            bottle_path = os.path.join(self.build_folder, ".rust-bottle.tar.gz")
            self.run(f'curl -fsSL -o "{bottle_path}" "{RUST_BOTTLE_URL}"')
            os.makedirs(rust_dir, exist_ok=True)
            # Bottle structure: rust/1.97.1/bin/cargo.real -> strip 2 levels
            self.run(f'tar xzf "{bottle_path}" -C "{rust_dir}" --strip-components=2')
            # Make binaries executable
            import stat as stat_mod
            for name in os.listdir(os.path.join(rust_dir, "bin")):
                p = os.path.join(rust_dir, "bin", name)
                if os.path.isfile(p):
                    os.chmod(p, os.stat(p).st_mode | stat_mod.S_IEXEC)

        if not os.path.isfile(cargo_path):
            raise ConanException("Failed to install Rust toolchain from Harmonybrew bottle")

        # Set up PATH so cargo can find rustc, and RUSTC for explicit rustc path
        env["RUSTC"] = rustc_path
        return cargo_path, rustc_path, env

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

        cargo, rustc, rust_env = self._ensure_rust()
        local_bin = self._ensure_cc()
        cargo_home = self._setup_cargo_mirror()

        # Build environment paths
        rust_bin = os.path.dirname(cargo)
        rust_lib = os.path.join(os.path.dirname(rust_bin), "lib")
        extra_path = rust_bin
        if local_bin:
            extra_path += ":" + local_bin

        # Set up SSL cert for cargo (HTTPS downloads from crates.io mirror)
        ssl_cert = os.environ.get("SSL_CERT_FILE", "/storage/Users/currentUser/usr/local/ssl/cert.pem")

        # Use a single shell command to set up environment and run cargo.
        # cargo.real is the actual binary (not the wrapper script).
        cmd = (
            f'export PATH="{extra_path}:$PATH" && '
            f'export CARGO_HOME="{cargo_home}" && '
            f'export RUSTC="{rustc}" && '
            f'export SSL_CERT_FILE="{ssl_cert}" && '
            f'export LD_LIBRARY_PATH="{rust_lib}:$LD_LIBRARY_PATH" && '
            f'"{cargo}" build --release'
        )
        self.run(cmd)

    def package(self):
        # Copy the release binary to bin/
        target_dir = os.path.join(self.build_folder, "target", "release")
        copy(self, "git-cliff", target_dir, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
