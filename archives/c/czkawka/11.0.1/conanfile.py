#!/usr/bin/env python3
"""Conan 2.x recipe — czkawka 11.0.1

Czkawka is a multi-tool written in Rust to find duplicates, empty files,
similar images, etc. This recipe builds the CLI frontend (czkawka_cli)
using cargo as the build system.

The Rust toolchain (cargo/rustc) must be pre-installed on the build machine.
On HarmonyOS, install via Harmonybrew: `brew install rust`.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class CzkawkaConan(ConanFile):
    name = "czkawka"
    version = "11.0.1"
    description = "Multi-tool to find duplicates, empty files, similar images, etc."
    license = "MIT"
    homepage = "https://github.com/qarmin/czkawka"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Resolve C/C++ compiler path from Conan conf or environment.
        clang = "clang"
        clangxx = "clang++"
        raw = self.conf_info.get("tools.build:compiler_executables", None)
        if raw:
            try:
                cemap = json.loads(raw) if isinstance(raw, str) else raw
                clang = cemap.get("c", clang)
                clangxx = cemap.get("cpp", clangxx)
            except (json.JSONDecodeError, TypeError):
                pass
        # Fall back to environment variables.
        clang = os.environ.get("CC", clang)
        clangxx = os.environ.get("CXX", clangxx)

        # On HarmonyOS, `cc` does not exist (only `clang`).
        # Rust's default linker for GNU targets uses `cc`.
        # Create a cc wrapper that delegates to clang.
        bin_dir = os.path.join(self.build_folder, "_cc_wrapper")
        os.makedirs(bin_dir, exist_ok=True)
        bash_path = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        for name, compiler in [("cc", clang), ("c++", clangxx)]:
            wrapper = os.path.join(bin_dir, name)
            with open(wrapper, "w") as f:
                f.write(f"#!{bash_path}\nexec {compiler} \"$@\"\n")
            os.chmod(wrapper, 0o755)

        # Build environment: prepend cc wrapper dir and common Rust locations.
        harmonybrew_bin = os.path.expanduser("~/.harmonybrew/bin")
        local_bin = os.path.expanduser("~/usr/local/bin")
        hnp_bin = "/data/service/hnp/bin"
        path_parts = [bin_dir, harmonybrew_bin, local_bin, hnp_bin]
        existing_path = os.environ.get("PATH", "")
        os.environ["PATH"] = ":".join(p for p in path_parts if p) + ":" + existing_path

        os.environ["CC"] = clang
        os.environ["CXX"] = clangxx
        os.environ["AR"] = "llvm-ar"
        os.environ["RANLIB"] = "llvm-ranlib"

        # TMPDIR for cargo (HarmonyOS /tmp is read-only).
        tmpdir = os.environ.get("TMPDIR") or os.path.expanduser("~/tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        # SSL certificates for cargo to download crates.
        ssl_cert = os.path.expanduser("~/usr/local/ssl/cert.pem")
        if os.path.exists(ssl_cert):
            os.environ["SSL_CERT_FILE"] = ssl_cert
            os.environ["CARGO_HTTP_CAINFO"] = ssl_cert

        # Run cargo build for the CLI sub-crate only.
        self.run("cargo build --release -p czkawka_cli")

    def package(self):
        # Cargo builds in the source folder, not the Conan build folder.
        # Check both source_folder and build_folder for the binary.
        candidates = [
            os.path.join(self.source_folder, "target", "release"),
            os.path.join(self.build_folder, "target", "release"),
            os.path.join(os.path.dirname(self.build_folder), "target", "release"),
        ]
        target_dir = None
        for d in candidates:
            if os.path.isfile(os.path.join(d, "czkawka_cli")):
                target_dir = d
                break
        if not target_dir:
            raise ConanException("czkawka_cli binary not found after build")
        copy(self, "czkawka_cli", target_dir, os.path.join(self.package_folder, "bin"))
        bin_path = os.path.join(self.package_folder, "bin", "czkawka_cli")
        if os.path.exists(bin_path):
            os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
