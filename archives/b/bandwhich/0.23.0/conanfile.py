#!/usr/bin/env python3
"""Conan recipe for bandwhich 0.23.0 — a Rust/Cargo CLI tool for network bandwidth monitoring.

Build system: Cargo (Rust)
Product: Executable (bandwhich)
Dependencies: libpcap (for pnet crate)
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BandwhichConan(ConanFile):
    name = "bandwhich"
    version = "0.23.0"
    description = "Display current network utilization by process, connection and remote IP/hostname"
    license = "MIT"
    homepage = "https://github.com/imsnif/bandwhich"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Set up environment for cargo to find libpcap via Conan dependency info
        libpcap_info = self.dependencies["libpcap"]
        libpcap_libdir = libpcap_info.cpp_info.libdir[0] if libpcap_info.cpp_info.libdir else ""
        libpcap_incdir = libpcap_info.cpp_info.includedirs[0] if libpcap_info.cpp_info.includedirs else ""

        if libpcap_libdir:
            pkgconfig_path = os.path.join(libpcap_libdir, "pkgconfig")
            if os.path.isdir(pkgconfig_path):
                existing = os.environ.get("PKG_CONFIG_PATH", "")
                os.environ["PKG_CONFIG_PATH"] = f"{pkgconfig_path}:{existing}" if existing else pkgconfig_path
            os.environ["LIBPCAP_LIB_DIR"] = libpcap_libdir
        if libpcap_incdir:
            os.environ["LIBPCAP_INCLUDE_DIR"] = libpcap_incdir

    def build(self):
        apply_conandata_patches(self)
        # Build with cargo (environment vars set in generate())
        self.run("cargo build --release")

    def package(self):
        # The binary may be in source_folder/target/release or build_folder/target/release
        search_dirs = [
            os.path.join(self.source_folder, "target", "release"),
            os.path.join(self.build_folder, "target", "release"),
        ]
        found = False
        for search_dir in search_dirs:
            binary = os.path.join(search_dir, "bandwhich")
            if os.path.isfile(binary):
                copy(self, "bandwhich", src=search_dir, dst=os.path.join(self.package_folder, "bin"))
                found = True
                break
        if not found:
            pattern = os.path.join(self.source_folder, "**", "release", "bandwhich")
            matches = glob.glob(pattern, recursive=True)
            if matches:
                src_dir = os.path.dirname(matches[0])
                copy(self, "bandwhich", src=src_dir, dst=os.path.join(self.package_folder, "bin"))
                found = True
        if not found:
            raise Exception("bandwhich binary not found after build")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
