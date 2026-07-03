#!/usr/bin/env python3
"""Conan recipe — fzf 0.67.0 (Go project).

fzf is a general-purpose command-line fuzzy finder written in Go.
Built with `go build` producing a static binary.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class FzfConan(ConanFile):
    name = "fzf"
    version = "0.67.0"
    description = "A command-line fuzzy finder written in Go"
    license = "MIT"
    homepage = "https://github.com/junegunn/fzf"
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
        # fzf is a Go project, build with go build
        self.run(
            'FZF_VERSION=0.67.0 FZF_REVISION=tarball CGO_ENABLED=1 '
            'go build -trimpath -ldflags "-s -w -X main.version=0.67.0 -X main.revision=tarball" -o fzf .'
        )

    def package(self):
        copy(self, "fzf", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        # Copy shell integration scripts and man pages
        copy(self, "*.sh", src=self.build_folder, dst=os.path.join(self.package_folder, "share", "fzf", "shell"))
        copy(self, "*.1", src=os.path.join(self.build_folder, "man", "man1"), dst=os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)

    def package_info(self):
        # fzf is a standalone binary, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Expose the bin directory
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
