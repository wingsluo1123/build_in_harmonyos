#!/usr/bin/env python3
"""Conan 2.x recipe — aztfexport 0.19.0 — Go project (go build).

aztfexport is a CLI tool to bring existing Azure resources into Terraform management.
Uses go build instead of configure/make.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AztfexportConan(ConanFile):
    name = "aztfexport"
    version = "0.19.0"
    description = "A tool to bring existing Azure resources under Terraform management"
    license = "MPL-2.0"
    homepage = "https://github.com/Azure/aztfexport"
    url = "https://github.com/Azure/aztfexport/archive/refs/tags/v0.19.0.tar.gz"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: Pure binary tool, no shared libraries to worry about
        pass

    def build(self):
        apply_conandata_patches(self)
        # Build Go project with OHOS-compatible settings
        # For OHOS (Linux-like), use GOOS=linux GOARCH=arm64
        env = {}
        if self.settings.os in ("Linux", "OHOS"):
            env["GOOS"] = "linux"
            env["GOARCH"] = "arm64"
        env["CGO_ENABLED"] = "0"

        goos = env.get("GOOS", "linux")
        goarch = env.get("GOARCH", "arm64")
        cgo = env.get("CGO_ENABLED", "0")

        # Set GOPROXY for environments where proxy.golang.org is unreachable
        goproxy = os.environ.get("GOPROXY", "https://goproxy.cn,https://goproxy.io,direct")
        self.run(
            f"GOOS={goos} GOARCH={goarch} CGO_ENABLED={cgo} "
            f"GOPROXY={goproxy} "
            f"go build -ldflags \"-X 'main.version={self.version}'\" -o aztfexport .",
            cwd=self.source_folder,
        )

    def package(self):
        # Copy the aztfexport binary to bin/
        copy(self, "aztfexport",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # Copy license
        copy(self, "LICENSE*",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # aztfexport is a pure binary tool, not a library
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
