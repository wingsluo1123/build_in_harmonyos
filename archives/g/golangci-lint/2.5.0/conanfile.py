#!/usr/bin/env python3
"""Conan recipe for golangci-lint 2.5.0 — Go project (go build).

golangci-lint is a fast Go linters runner.
This recipe builds the golangci-lint CLI binary using `go build`.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class GolangciLintConan(ConanFile):
    name = "golangci-lint"
    version = "2.5.0"
    description = "Fast Go linters runner — aggregates 100+ Go linters"
    license = "MIT"
    homepage = "https://github.com/golangci/golangci-lint"
    url = ""  # CI fills this

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Go build with CGO disabled for static binary
        # Must cd to source folder where go.mod lives
        src = self.source_folder
        self.run(
            f"cd {src} && "
            "CGO_ENABLED=0 "
            "GOPROXY=https://goproxy.cn,direct "
            "GOSUMDB=off "
            "GOTOOLCHAIN=auto "
            "go build -trimpath "
            "-ldflags '-s -w -X main.version=2.5.0 -X main.date=2026-07-02 -X main.commit=v2.5.0' "
            "-o golangci-lint ./cmd/golangci-lint"
        )

    def package(self):
        copy(self, "golangci-lint", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # golangci-lint is a standalone binary, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Expose the bin directory
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
