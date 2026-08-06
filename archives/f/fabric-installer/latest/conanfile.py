#!/usr/bin/env python3
"""Conan recipe for fabric-installer — Hyperledger Fabric installation script.

Shell script tool that downloads and installs Hyperledger Fabric binaries,
docker images, and samples. No compilation needed — the script is packaged
as-is for distribution via Conan.
"""
import os

from conan import ConanFile
from conan.tools.files import download, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class FabricInstallerConan(ConanFile):
    name = "fabric-installer"
    version = "latest"
    description = "Hyperledger Fabric installation script for downloading Fabric components"
    license = "Apache-2.0"
    homepage = "https://hyperledger-fabric.readthedocs.io"
    url = ""

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        download(self, filename="install-fabric.sh", **self.conan_data["sources"])

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        copy(self, "install-fabric.sh", src=self.source_folder, dst=bin_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
