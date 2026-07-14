#!/usr/bin/env python3
"""Conan recipe — bossa 1.9.1 (Makefile)

BOSSA (Basic Open Source SAM-BA Application) — Flash programmer for
Atmel SAM microcontrollers. Provides CLI tools bossac and bossash.
GUI tool bossa requires wxWidgets (unavailable on OHOS), not built.

Build system: pure Makefile (no configure).
The Makefile detects OS via `uname -s | cut -c -7`. On OHOS this returns
"Harmony" which matches no platform rule, so we override OS=Linux to get
PosixSerialPort.cpp and LinuxPortFactory.cpp (OHOS is POSIX-compatible).
Make targets are path-based: bin/bossac, bin/bossash (not bare names).

readline dependency: readline/8.2 is installed as a pre-compiled system
package (cmd-pkgs) at ~/usr/local/. Not yet published to Conan registry,
so declared as a system dependency rather than a Conan requires.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BossaConan(ConanFile):
    name = "bossa"
    version = "1.9.1"
    description = "Flash programmer for Atmel SAM microcontrollers (bossac + bossash CLI tools)"
    license = "BSD-3-Clause"
    homepage = "https://www.shumatech.com/forum/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self, build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars
        # Conan 2.29.1: tools.build:compiler_executables is a dict, not individual keys
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"

        # readline is installed as a pre-compiled system package (cmd-pkgs)
        # at ~/usr/local/ (R18: pre-compiled packages take priority)
        local_prefix = os.path.expanduser("~/usr/local")
        readline_inc = os.path.join(local_prefix, "include")
        readline_lib = os.path.join(local_prefix, "lib")

        if not os.path.exists(os.path.join(readline_inc, "readline", "readline.h")):
            raise ConanInvalidConfiguration(
                "readline headers not found. Install with: "
                "curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- readline 8.2"
            )

        # Build only CLI tools: bin/bossac and bin/bossash (not GUI bossa which needs wxWidgets)
        # OS=Linux: OHOS uname returns "Harmony" which matches no Makefile platform rule;
        #   overriding to Linux activates PosixSerialPort.cpp + LinuxPortFactory.cpp (OHOS is POSIX)
        # VERSION=1.9.1 overrides `git describe` which fails in non-git source dir
        # R9: Always use -j1
        self.run(
            f'make OS=Linux CXX={cxx} VERSION=1.9.1 '
            f'CXXFLAGS="-fPIC -O2 -Wno-error -I{readline_inc}" '
            f'LDFLAGS="-L{readline_lib}" '
            f'bin/bossac bin/bossash -j1'
        )

    def package(self):
        # Copy built binaries from source bin/ to package bin/
        copy(self, "bossac", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "bossash", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "bin"))

        # OHOS: ELF binaries must be signed to be executable
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        for bin_name in ("bossac", "bossash"):
            bin_path = os.path.join(self.package_folder, "bin", bin_name)
            if os.path.exists(sign_tool) and os.path.exists(bin_path):
                signed_path = bin_path + ".signed"
                self.run(
                    f"{sign_tool} sign -selfSign 1 "
                    f"-inFile {bin_path} -outFile {signed_path} "
                    f"-signAlg SHA256withECDSA -keyAlias {bin_name}"
                )
                os.replace(signed_path, bin_path)
                os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["readline"]
