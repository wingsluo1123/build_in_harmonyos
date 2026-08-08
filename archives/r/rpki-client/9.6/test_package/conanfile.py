#!/usr/bin/env python3
"""Conan test_package — rpki-client 9.6.

rpki-client is a command-line tool. The L1 test verifies the installed binary
runs correctly by checking `rpki-client -V` output.

R34: test.c calls rpki-client -V via popen() and verifies "9.6"
is in the output. The rpki-client binary path is passed via RPKI_CLIENT_BIN
CMake variable, which CTest sets as RPKI_CLIENT_PATH env var for the test binary.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RpkiClientTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        pass

    def test(self):
        cmake = CMake(self)
        # Pass rpki-client binary path to CMake
        bin_path = os.path.join(
            self.dependencies["rpki-client"].package_folder,
            "sbin", "rpki-client"
        )
        if not os.path.exists(bin_path):
            bin_path = os.path.join(
                self.dependencies["rpki-client"].package_folder,
                "bin", "rpki-client"
            )

        # Set LD_LIBRARY_PATH for runtime deps (expat, musl-fts)
        dep_libs = []
        for dep_name in ["libressl", "musl-fts", "expat", "zlib"]:
            try:
                dep = self.dependencies[dep_name]
                if dep.package_folder:
                    lib = os.path.join(dep.package_folder, "lib")
                    if os.path.isdir(lib):
                        dep_libs.append(lib)
            except (KeyError, Exception):
                pass
        if dep_libs:
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = ":".join(
                dep_libs + ([existing] if existing else []))

        cmake.configure(variables={"RPKI_CLIENT_BIN": bin_path})
        cmake.build()
        cmake.test()
        # Also verify binary runs directly
        if os.path.exists(bin_path):
            self.run(f'"{bin_path}" -V')
