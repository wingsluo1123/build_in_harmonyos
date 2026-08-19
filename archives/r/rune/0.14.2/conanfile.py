#!/usr/bin/env python3
"""Conan 2.x recipe for Rune 0.14.2 on Linux and HarmonyOS."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RuneConan(ConanFile):
    name = "rune"
    version = "0.14.2"
    description = "Interpreter for the Rune embeddable dynamic programming language"
    license = "MIT OR Apache-2.0"
    homepage = "https://rune-rs.github.io"
    url = "https://github.com/rune-rs/rune"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rune supports Linux and OHOS only, got {self.settings.os}"
            )
        if str(self.settings.arch) != "armv8" and str(self.settings.os) == "OHOS":
            raise ConanInvalidConfiguration("rune for OHOS currently supports armv8 only")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        cargo_dir = os.path.join(self.source_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        with open(os.path.join(cargo_dir, "config.toml"), "w", encoding="utf-8") as config:
            config.write(
                '[source.crates-io]\n'
                'replace-with = "rsproxy-sparse"\n\n'
                '[source.rsproxy-sparse]\n'
                'registry = "sparse+https://rsproxy.cn/index/"\n'
            )
            if str(self.settings.os) == "OHOS":
                config.write(
                    '\n[target.aarch64-unknown-linux-ohos]\n'
                    'linker = "clang"\n'
                )

    def build(self):
        apply_conandata_patches(self)
        if not shutil.which("cargo"):
            raise ConanInvalidConfiguration(
                "Rust cargo is required; install the HarmonyOS Rust toolchain before building"
            )

        if str(self.settings.os) == "OHOS":
            tmpdir = os.path.expanduser("~/tmp/rune")
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir

        manifest = os.path.join(self.source_folder, "Cargo.toml")
        target = os.path.join(self.build_folder, "target")
        self.run(
            f'cargo build --release -p rune-cli --manifest-path "{manifest}" '
            f'--target-dir "{target}"',
            env="conanbuild",
        )
        self.run(
            f'cargo test --release -p rune --lib --manifest-path "{manifest}" '
            f'--target-dir "{target}"',
            env="conanbuild",
        )

    def package(self):
        release_dir = os.path.join(self.build_folder, "target", "release")
        copy(self, "rune", release_dir, os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE-*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
