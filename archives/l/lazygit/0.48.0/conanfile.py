#!/usr/bin/env python3
"""Conan recipe — lazygit 0.48.0 (Go project).

lazygit is a simple terminal UI for git commands, written in Go.
Built with `go build` producing a static binary with cgo enabled.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class LazygitConan(ConanFile):
    name = "lazygit"
    version = "0.48.0"
    description = "A simple terminal UI for git commands, written in Go"
    license = "MIT"
    homepage = "https://github.com/jesseduffield/lazygit"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        # Apply patches (if any from conandata.yml)
        apply_conandata_patches(self)
        # lazygit is a Go project, build with go build
        # CGO_ENABLED=1 for terminal UI (tcell) cgo dependencies
        # -mod=vendor to use vendored dependencies
        self.run(
            'CGO_ENABLED=1 GOFLAGS=-mod=vendor '
            'go build -trimpath -ldflags '
            '"-s -w -X main.commit=v0.48.0 -X main.version=0.48.0 -X main.date=2025-01-01" '
            '-o lazygit .'
        )

    def package(self):
        copy(self, "lazygit", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # lazygit is a standalone binary, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Expose the bin directory
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
