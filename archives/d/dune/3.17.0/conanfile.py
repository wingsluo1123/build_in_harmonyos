#!/usr/bin/env python3
"""Conan recipe — Dune 3.17.0 (OCaml build system)

Dune uses its own bootstrap mechanism:
  1. ocaml boot/bootstrap.ml  → builds _boot/dune.exe
  2. make release             → builds @install with --profile dune-bootstrap

Patches:
  - boot/duneboot.ml: prefer bytecode over .opt native binaries (OHOS security)
  - src/dune_rules/which.ml: don't prefer .opt variants in compiler detection
  - vendor/spawn/src/spawn_stubs.c: guard pthread_setcancelstate for OHOS
  - dune-project: add (version 3.17.0)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class DuneConan(ConanFile):
    name = "dune"
    version = "3.17.0"
    description = "Fast, portable, and opinionated build system for OCaml"
    license = "MIT"
    homepage = "https://github.com/ocaml/dune"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Step 1: Bootstrap - build _boot/dune.exe
        self.run("ocaml boot/bootstrap.ml", cwd=self.source_folder)
        # Step 2: Release build
        self.run("make release", cwd=self.source_folder)

    def package(self):
        # Copy the built binary and install artifacts
        copy(self, "dune.exe",
             src=os.path.join(self.source_folder, "_build", "default", "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        # Copy install tree (doc, lib, man, share)
        copy(self, "*",
             src=os.path.join(self.source_folder, "_build", "install", "default"),
             dst=self.package_folder, keep_path=True, excludes=["bin/*"])
        # Ensure bin/dune is the actual binary (not a symlink)
        bin_dune = os.path.join(self.package_folder, "bin", "dune")
        bin_dune_exe = os.path.join(self.package_folder, "bin", "dune.exe")
        if os.path.islink(bin_dune):
            os.unlink(bin_dune)
        if os.path.exists(bin_dune_exe):
            os.rename(bin_dune_exe, bin_dune)

    def package_info(self):
        self.cpp_info.libs = []
        # Dune is a build tool, expose it via bindirs
        self.cpp_info.bindirs = ["bin"]
