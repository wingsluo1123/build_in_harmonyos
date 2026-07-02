#!/usr/bin/env python3
"""Conan recipe — Menhir (OCaml parser generator) using Dune build system.

Menhir is an LR(1) parser generator for OCaml. It uses a multi-stage
bootstrap build via Dune. The final executable is installed as 'menhir'.

Build dependencies: OCaml 4.14+, Dune 3.0+
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MenhirConan(ConanFile):
    name = "menhir"
    version = "20260209"
    description = "Menhir — an LR(1) parser generator for OCaml"
    license = "MIT"
    homepage = "https://gitlab.inria.fr/fpottier/menhir"
    url = ""  # CI fills this

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # Menhir requires OCaml and Dune as build tools
        # These are expected to be pre-installed in the build environment
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        # Build using Dune — only the install targets (excludes demos, benchmarks)
        # R9: Use -j1 for bootstrap safety (stage1 → stage2 dependency)
        self.run("dune build --profile release --root . @install -j1", env="conanbuild")

    def package(self):
        # Install using Dune to the package folder
        prefix = os.path.join(self.package_folder)
        self.run(f"dune install --prefix={prefix} --root .", env="conanbuild")

    def package_info(self):
        # Menhir is primarily a command-line tool
        self.cpp_info.libs = []
        # The binary is in bin/
        bin_path = os.path.join(self.package_folder, "bin")
        self.output.info(f"menhir binary: {os.path.join(bin_path, 'menhir')}")
