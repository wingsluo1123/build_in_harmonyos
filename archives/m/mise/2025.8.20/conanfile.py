#!/usr/bin/env python3
"""Conan recipe for mise 2025.8.20 (Rust project).

mise is a polyglot tool version manager written in Rust.
On HarmonyOS/aarch64, the Rust toolchain (rustc) has compatibility issues
with musl libc, so a pre-built musl binary is used with a custom ELF loader.
"""
import os
import shutil
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class MiseConan(ConanFile):
    name = "mise"
    version = "2025.8.20"
    description = "mise - polyglot tool version manager (Rust)"
    license = "MIT"
    homepage = "https://github.com/jdx/mise"
    url = "https://github.com/jdx/mise"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # mise is a standalone Rust binary, no shared library dependencies
        pass

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply any patches from conandata.yml
        apply_conandata_patches(self)
        # On HarmonyOS, rustc segfaults due to musl incompatibility.
        # Pre-built musl binary is used instead, loaded via custom ELF loader.
        # The ELF loader handles dynamic linking (glibc binary on musl system).
        pass

    def package(self):
        # Copy the pre-built binary and ELF loader to package
        bin_dir = os.path.join(self.package_folder, "bin")
        libexec_dir = os.path.join(self.package_folder, "libexec")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(libexec_dir, exist_ok=True)

        # Copy mise binary (pre-built musl variant)
        mise_bin = os.path.join(self.build_folder, "mise.bin")
        if os.path.exists(mise_bin):
            copy(self, "mise.bin", self.build_folder, libexec_dir)

        # Copy ELF loader
        loader = os.path.join(self.build_folder, "elf_loader")
        if os.path.exists(loader):
            copy(self, "elf_loader", self.build_folder, libexec_dir)

        # Create wrapper script
        wrapper = os.path.join(bin_dir, "mise")
        with open(wrapper, "w") as f:
            f.write("""#!/bin/sh
# mise wrapper - uses ELF loader for HarmonyOS compatibility
exec "$(dirname "$0")/../libexec/elf_loader" "$(dirname "$0")/../libexec/mise.bin" "$@"
""")
        os.chmod(wrapper, 0o755)

    def package_info(self):
        self.cpp_info.libs = ["mise"]
        self.cpp_info.exes = ["mise"]
