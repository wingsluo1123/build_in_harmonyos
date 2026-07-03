#!/usr/bin/env python3
"""Conan recipe for aztfexport 0.19.0 — Go project (pure binary tool).

aztfexport is Azure's Terraform resource export tool, written in Go.
It produces a single static binary (CGO_ENABLED=0) that requires no shared libraries.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv


class AztfexportConan(ConanFile):
    name = "aztfexport"
    version = "0.19.0"
    description = "Azure Terraform resource export tool"
    license = "MPL-2.0"
    homepage = "https://github.com/Azure/aztfexport"
    url = "https://github.com/Azure/aztfexport"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()

    def build(self):
        apply_conandata_patches(self)

        goos = {"Linux": "linux", "OHOS": "linux", "Windows": "windows", "Macos": "darwin"}.get(
            str(self.settings.os), "linux"
        )
        goarch = {"x86_64": "amd64", "armv8": "arm64", "armv7": "arm"}.get(
            str(self.settings.arch), "arm64"
        )

        build_cmd = (
            f'CGO_ENABLED=0 GOOS={goos} GOARCH={goarch} '
            f'GOPROXY=https://goproxy.cn,direct '
            f'go build -trimpath '
            f'-ldflags="-s -w -X \'main.version={self.version}\' -X \'main.revision=conan\'" '
            f'-o {os.path.join(self.build_folder, "aztfexport")} .'
        )
        self.run(build_cmd, cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "aztfexport", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.frameworkdirs = []
        self.cpp_info.resdirs = []
