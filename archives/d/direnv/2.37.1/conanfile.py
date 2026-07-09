#!/usr/bin/env python3
"""Conan recipe — direnv 2.37.1 (Go project).

direnv is an environment variable manager for your shell.
Built with `go build` producing a static binary.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class DirenvConan(ConanFile):
    name = "direnv"
    version = "2.37.1"
    description = "direnv is an environment variable manager for your shell"
    license = "MIT"
    homepage = "https://github.com/direnv/direnv"
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
        # direnv is a Go project, build with go build
        self.run(
            'CGO_ENABLED=0 go build -trimpath '
            '-ldflags "-s -w -X github.com/direnv/direnv/v2/version.Version=2.37.1" '
            '-o direnv .'
        )

    def package(self):
        copy(self, "direnv", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        # Copy man pages if available
        copy(self, "*.1", src=os.path.join(self.build_folder, "man", "man1"), dst=os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)

    def package_info(self):
        # direnv is a standalone binary, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Expose the bin directory
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
