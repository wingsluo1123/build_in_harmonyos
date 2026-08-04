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
        # Set up environment for cargo to find libpcap
        libpcap_info = self.dependencies["libpcap"]
        libpcap_libdir = libpcap_info.cpp_info.libdir[0] if libpcap_info.cpp_info.libdir else ""
        libpcap_incdir = libpcap_info.cpp_info.includedirs[0] if libpcap_info.cpp_info.includedirs else ""

        envvars = []
        if libpcap_libdir:
            pkgconfig_path = f"{libpcap_libdir}/pkgconfig"
            if os.path.isdir(pkgconfig_path):
                existing = os.environ.get("PKG_CONFIG_PATH", "")
                envvars.append(f"PKG_CONFIG_PATH={pkgconfig_path}:{existing}" if existing else f"PKG_CONFIG_PATH={pkgconfig_path}")
            envvars.append(f"LIBPCAP_LIB_DIR={libpcap_libdir}")
        if libpcap_incdir:
            envvars.append(f"LIBPCAP_INCLUDE_DIR={libpcap_incdir}")
        self._build_env = envvars

    def build(self):
        apply_conandata_patches(self)
        # Build with cargo
        self.run("cargo build --release", env=getattr(self, "_build_env", None))

    def package(self):
        # The binary may be in source_folder/target/release or build_folder/target/release
        # depending on layout. Search both.
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
            # Last resort: glob search
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
