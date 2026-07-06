#!/usr/bin/env python3
"""Conan recipe — blake3 C library (direct compilation).

blake3 is a fast cryptographic hash function. The C implementation is a single
file (blake3.c) with blake3.h header. We compile directly with clang instead
of using the CMake build system, which has a complex directory structure.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Blake3Conan(ConanFile):
    name = "blake3"
    version = "1.8.3"
    description = "Fast cryptographic hash function (C implementation)"
    license = "Apache-2.0"
    homepage = "https://github.com/BLAKE3-team/BLAKE3"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass  # No CMake toolchain needed

    def build(self):
        apply_conandata_patches(self)
        c_dir = os.path.join(self.source_folder, "c")
        # Compile blake3.c - disable x86 SIMD, use NEON for aarch64
        obj = os.path.join(self.build_folder, "blake3.o")
        lib = os.path.join(self.build_folder, "libblake3.a")
        self.run(
            f"clang -c -O3 -DBLAKE3_NO_SSE2 -DBLAKE3_NO_AVX2 -DBLAKE3_NO_AVX512 -DBLAKE3_NO_SSE41 "
            f"-I{c_dir} "
            f"-o {obj} "
            f"{os.path.join(c_dir, 'blake3.c')}",
            env="conanbuild"
        )
        self.run(f"ar rcs {lib} {obj}", env="conanbuild")

    def package(self):
        c_dir = os.path.join(self.source_folder, "c")
        copy(self, "blake3.h", c_dir, os.path.join(self.package_folder, "include"))
        copy(self, "libblake3.a", self.build_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["blake3"]
