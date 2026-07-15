#!/usr/bin/env python3
"""Conan recipe — tcping 2.1.0

tcping: non-blocking TCP connection test utility.
Homepage: https://github.com/mkirchner/tcping
License: MIT
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TcpingConan(ConanFile):
    name = "tcping"
    version = "2.1.0"
    description = "Non-blocking TCP connection test utility"
    license = "MIT"
    homepage = "https://github.com/mkirchner/tcping"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Get compiler from Conan build environment (set by profile), fallback to clang
        cc = os.environ.get("CC", "clang")
        # Simple Makefile project: compile cli.c and tcping.c into tcping binary
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        # Copy the compiled binary to the package bin/ directory
        copy(self, "tcping", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # tcping is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
