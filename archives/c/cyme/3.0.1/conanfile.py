#!/usr/bin/env python3
"""Conan recipe — cyme 3.0.1 (Rust/cargo project).

cyme is a cross-platform lsusb alternative written in Rust.
It uses nusb (pure Rust USB) for device enumeration on OHOS.

Build: cargo build --release --no-default-features --features nusb,regex_icon,watch,bin
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CymeConan(ConanFile):
    name = "cyme"
    version = "3.0.1"
    description = "List system USB buses and devices. A modern cross-platform lsusb"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/tuna-f1sh/cyme"
    url = "https://github.com/tuna-f1sh/cyme"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # cyme has no Conan dependencies — all Rust deps are managed by cargo
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os in ("Linux", "OHOS"):
            pass  # native build, no cross-compilation needed
        # No CMake/Autotools toolchain needed — cargo handles everything

    def build(self):
        apply_conandata_patches(self)

        # Dynamically collect library paths (no hardcoded absolute paths)
        import subprocess
        import shutil

        # Start with existing LD_LIBRARY_PATH (preserves CI environment setup)
        paths = [p for p in os.environ.get("LD_LIBRARY_PATH", "").split(":") if p]

        # 1. Get rust sysroot library path via rustc
        try:
            rust_sysroot = subprocess.check_output(
                ["rustc", "--print", "sysroot"], text=True).strip()
            rust_lib = os.path.join(rust_sysroot, "lib")
            if rust_lib and rust_lib not in paths:
                paths.append(rust_lib)
        except Exception:
            pass

        # 2. Find OpenSSL library path near cargo binary
        #    cargo.real links libssl.so.3 / libcrypto.so.3 dynamically;
        #    locate the lib/ dir containing them by walking up from cargo.
        cargo_path = shutil.which("cargo")
        if cargo_path:
            cargo_real = os.path.realpath(cargo_path)
            d = os.path.dirname(cargo_real)
            for _ in range(6):  # walk up at most 6 levels
                lib_dir = os.path.join(d, "lib")
                if (os.path.isfile(os.path.join(lib_dir, "libssl.so.3")) or
                    os.path.isfile(os.path.join(lib_dir, "libcrypto.so.3"))):
                    if lib_dir not in paths:
                        paths.insert(0, lib_dir)
                    break
                d = os.path.dirname(d)

        os.environ["LD_LIBRARY_PATH"] = ":".join(paths)

        # CARGO_HOME uses default user location (no hardcoded paths)
        os.environ.setdefault("CARGO_HOME", os.path.expanduser("~/.cargo"))

        # Build with cargo — disable udev feature (udevrs has OHOS libc incompatibility)
        # Use nusb (pure Rust USB) instead
        build_cmd = (
            "cargo build --release "
            "--no-default-features "
            "--features nusb,regex_icon,watch,bin"
        )
        self.run(build_cmd)

    def package(self):
        # Install the binary
        copy(self, "cyme",
             src=os.path.join(self.source_folder, "target", "release"),
             dst=os.path.join(self.package_folder, "bin"))

        # Install man pages and completions
        copy(self, "cyme.1",
             src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "cyme.bash",
             src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "share", "bash-completion", "completions"))
        copy(self, "_cyme",
             src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "share", "zsh", "site-functions"))
        copy(self, "cyme.fish",
             src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "share", "fish", "completions"))

    def package_info(self):
        # cyme is an executable, not a library — no cpp_info.libs needed
        self.cpp_info.libs = []
        # Add bin to PATH for consumers
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
