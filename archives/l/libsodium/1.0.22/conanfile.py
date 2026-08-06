#!/usr/bin/env python3
"""Conan recipe for libsodium 1.0.22 — modern cryptographic library (NaCl).

libsodium is a modern, easy-to-use software library for key generation,
encryption, decryption, signatures, hashing, and password hashing.

Build system: Autotools (configure + make).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibsodiumConan(ConanFile):
    name = "libsodium"
    version = "1.0.22"
    description = "Modern cryptographic library (NaCl)"
    license = "ISC"
    homepage = "https://libsodium.org/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libsodium is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Fix for HarmonyOS: config.guess doesn't recognize OHOS, and /tmp
        # is read-only so the compile-test in config.guess fails too.
        # Pass --build explicitly to skip auto-detection.
        if self.settings.os == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["sodium"]
