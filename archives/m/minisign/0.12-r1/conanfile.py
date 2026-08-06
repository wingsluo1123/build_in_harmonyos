#!/usr/bin/env python3
"""Conan recipe for minisign 0.12-r1 — dead simple tool to sign files and verify signatures.

minisign is a CLI tool by Frank Denis that uses Ed25519 signatures via libsodium.
Dependencies:
  - libsodium/1.0.22 (cryptography library)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MinisignConan(ConanFile):
    name = "minisign"
    version = "0.12-r1"
    description = "Dead simple tool to sign files and verify signatures"
    license = "ISC"
    homepage = "https://github.com/jedisct1/minisign"

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libsodium/1.0.22")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"minisign is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Pass libsodium paths from Conan dependency to CMake
        sodium = self.dependencies["libsodium"]
        tc.variables["SODIUM_INCLUDE_DIR"] = sodium.cpp_info.includedirs[0]
        # Build the actual library file path (not just the directory)
        lib_dir = sodium.cpp_info.libdirs[0]
        # Try shared first, then static
        for ext in [".so", ".a", ".dylib"]:
            for lib in sodium.cpp_info.libs:
                lib_path = os.path.join(lib_dir, f"lib{lib}{ext}")
                if os.path.exists(lib_path):
                    tc.variables["SODIUM_LIBRARY"] = lib_path
                    break
            if "SODIUM_LIBRARY" in tc.variables:
                break
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # minisign is a CLI tool — expose bindirs for consumers
        self.cpp_info.bindirs = ["bin"]
