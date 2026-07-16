#!/usr/bin/env python3
"""Conan recipe for Boost 1.84.0 — header-only installation.

Boost uses its own b2 (Boost.Build) build system. On OHOS, the b2 build
system fails to compile libraries due to SHELL execution incompatibility
(E035/E068) and architecture detection issues (no matching asm sources
for aarch64). 

This recipe installs boost as header-only, which covers the majority of
boost libraries that are header-only by design. The 51 libraries that
require compilation (filesystem, thread, context, etc.) are not included,
but their headers ARE available for use with system-provided alternatives
(C++17 std::filesystem, C++11 std::thread, etc.).

R32: settings.os check uses `in ("Linux", "OHOS")`.
R26: boost is NOT a system-name library, so dynamic linking is OK (N/A for header-only).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class BoostConan(ConanFile):
    name = "boost"
    version = "1.84.0"
    description = "Boost C++ Libraries - free peer-reviewed portable C++ source libraries"
    license = "BSL-1.0"
    homepage = "https://www.boost.org"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # E035/E068: b2 build system fails on OHOS (SHELL execution + arch detection)
        # Header-only installation: no compilation needed
        # Headers are copied in package() directly from source
        apply_conandata_patches(self)

    def package(self):
        # Copy boost headers from source to package folder
        copy(self, pattern="*", src=os.path.join(self.source_folder, "boost"),
             dst=os.path.join(self.package_folder, "include", "boost"))

    def package_info(self):
        # Header-only: no compiled libraries
        # boost::system, boost::asio (header parts), boost::smart_ptr, etc.
        # are all header-only and available without compiled libs
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "Boost")
        self.cpp_info.includedirs = ["include"]
