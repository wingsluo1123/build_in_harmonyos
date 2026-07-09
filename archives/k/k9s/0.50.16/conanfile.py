#!/usr/bin/env python3
"""Conan recipe — k9s 0.50.16 (Go project).

k9s is a Kubernetes TUI (Terminal User Interface) written in Go.
Built with `go build` producing a static binary.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class K9sConan(ConanFile):
    name = "k9s"
    version = "0.50.16"
    description = "Kubernetes TUI — a terminal UI for managing Kubernetes clusters"
    license = "Apache-2.0"
    homepage = "https://github.com/derailed/k9s"
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
        # k9s is a Go project, build with go build
        # CGO_ENABLED=0 for pure Go static binary (tcell uses syscalls, no C deps)
        self.run(
            'CGO_ENABLED=0 '
            'go build -trimpath '
            '-ldflags "-s -w -X github.com/derailed/k9s/cmd.version=v0.50.16" '
            '-tags netgo -o k9s .'
        )

    def package(self):
        copy(self, "k9s", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # k9s is a standalone binary, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Expose the bin directory
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
