#!/usr/bin/env python3
"""Conan recipe for Apollo Rover v0.40.0 — Rust/Cargo project.

Rover is a CLI tool for working with the Apollo GraphQL Registry.
Build system: Cargo (Rust).

Key adaptations for OHOS:
  - Switched crypto provider from aws-lc-rs to ring (aws-lc-sys assembly
    generation fails on OHOS due to missing Perl/Go integration in cmake)
  - All reqwest features changed from "rustls" to "rustls-no-provider"
  - Added explicit rustls/hyper-rustls/tokio-rustls deps with "ring" feature
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, unzip, export_conandata_patches, apply_conandata_patches


class RoverConan(ConanFile):
    name = "rover"
    version = "latest"
    description = "Apollo Rover - CLI tool for working with the Apollo GraphQL Registry"
    license = "MIT"
    homepage = "https://github.com/apollographql/rover"
    url = "https://github.com/apollographql/rover"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rover {self.version} is only supported on Linux/OHOS, "
                f"not {self.settings.os}"
            )

    def requirements(self):
        pass

    def build_requirements(self):
        pass

    def source(self):
        url = self.conan_data["sources"]["url"]
        sha256 = self.conan_data["sources"]["sha256"]
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception:
            # Fallback 1: curl -k for OHOS where Python SSL module is unavailable
            import hashlib
            filename = os.path.basename(url)
            try:
                self.run(f'curl -kL -o "{filename}" "{url}"', cwd=self.source_folder)
                filepath = os.path.join(self.source_folder, filename)
                with open(filepath, "rb") as f:
                    actual_sha = hashlib.sha256(f.read()).hexdigest()
                if actual_sha != sha256:
                    raise ConanInvalidConfiguration(
                        f"SHA256 mismatch: expected {sha256}, got {actual_sha}"
                    )
                unzip(self, filename, destination=self.source_folder, strip_root=True)
            except Exception:
                # Fallback 2: local tarball (GitHub unreachable in CI)
                local_tarball = os.path.expanduser("~/tmp/builds/rover-latest.tar.gz")
                if not os.path.exists(local_tarball):
                    local_tarball = os.path.join(
                        os.environ.get("TMPDIR", os.path.expanduser("~/tmp")),
                        "builds", "rover-latest.tar.gz"
                    )
                if os.path.exists(local_tarball):
                    self.output.info(f"Using local tarball: {local_tarball}")
                    with open(local_tarball, "rb") as f:
                        actual_sha = hashlib.sha256(f.read()).hexdigest()
                    if actual_sha != sha256:
                        raise ConanInvalidConfiguration(
                            f"Local tarball SHA256 mismatch: expected {sha256}, got {actual_sha}"
                        )
                    unzip(self, local_tarball, destination=self.source_folder, strip_root=True)
                else:
                    raise

    def _find_or_install_cargo(self):
        """Find cargo binary, install Rust if not found."""
        cargo = shutil.which("cargo")
        if cargo:
            return cargo
        brew_cargo = os.path.expanduser("~/.harmonybrew/bin/cargo")
        if os.path.isfile(brew_cargo) and os.access(brew_cargo, os.X_OK):
            return brew_cargo
        self.output.info("cargo not found, installing Rust via cmd-pkgs...")
        import subprocess
        try:
            subprocess.run(
                ["bash", "-c",
                 "curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- rust"],
                check=True, timeout=600
            )
        except Exception as e:
            raise ConanInvalidConfiguration(
                f"cargo not found and Rust installation failed: {e}")
        cargo = shutil.which("cargo")
        if cargo:
            return cargo
        brew_cargo = os.path.expanduser("~/.harmonybrew/bin/cargo")
        if os.path.isfile(brew_cargo) and os.access(brew_cargo, os.X_OK):
            return brew_cargo
        raise ConanInvalidConfiguration("cargo not found after Rust installation")

    def _find_ohos_lib_dir(self):
        """Find the OHOS SDK C++ library directory (E212 fix)."""
        import glob
        candidates = [
            os.path.expanduser("~/.harmonybrew/Cellar/ohos-sdk/26.0.0.18_1/native/llvm/lib/aarch64-linux-ohos"),
            os.path.expanduser("~/.harmonybrew/Cellar/ohos-sdk/*/native/llvm/lib/aarch64-linux-ohos"),
        ]
        for pattern in candidates:
            for path in glob.glob(pattern):
                if os.path.isdir(path):
                    return path
        return None

    def _setup_libstdcxx(self, lib_dir):
        """Create libstdc++ linker scripts pointing to libc++ (E212 workaround)."""
        libstdcxx_so = os.path.join(lib_dir, "libstdc++.so")
        if not os.path.exists(libstdcxx_so):
            with open(libstdcxx_so, "w") as f:
                f.write("INPUT(-lc++_shared)\n")
        libstdcxx_a = os.path.join(lib_dir, "libstdc++.a")
        if not os.path.exists(libstdcxx_a):
            with open(libstdcxx_a, "w") as f:
                f.write("INPUT(-lc++_static -lc++abi)\n")

    def build(self):
        apply_conandata_patches(self)
        cargo = self._find_or_install_cargo()

        # E002: OHOS /tmp is read-only, use $HOME/tmp
        tmpdir = os.path.expanduser("~/tmp")
        os.makedirs(tmpdir, exist_ok=True)

        # E212: Rust linker defaults to -lstdc++ but OHOS only has libc++
        ohos_sdk_lib = self._find_ohos_lib_dir()
        if ohos_sdk_lib:
            self._setup_libstdcxx(ohos_sdk_lib)

        # Set environment variables for cargo build
        old_env = {}
        env_vars = {
            "CARGO_HOME": os.path.join(self.build_folder, ".cargo-home"),
            "CARGO_NET_GIT_FETCH_WITH_CLI": "true",
            "TMPDIR": tmpdir,
            "TEMP": tmpdir,
            "TMP": tmpdir,
        }
        # RUSTFLAGS with OHOS lib dir for linker
        rustflags = ["-C", "link-arg=-Wl,--gc-sections"]
        if ohos_sdk_lib:
            rustflags.append(f"-L {ohos_sdk_lib}")
            rustflags.append(f"-C link-arg=-L{ohos_sdk_lib}")
        env_vars["RUSTFLAGS"] = " ".join(rustflags)

        for k, v in env_vars.items():
            old_env[k] = os.environ.get(k)
            os.environ[k] = v

        try:
            self.run(f'"{cargo}" build --release -j2', cwd=self.source_folder)
        finally:
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def package(self):
        bin_dir = os.path.join(self.source_folder, "target", "release")
        copy(
            self,
            "rover",
            src=bin_dir,
            dst=os.path.join(self.package_folder, "bin"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.builddirs = []
        self.cpp_info.bindirs = ["bin"]
