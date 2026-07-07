#!/usr/bin/env python3
"""Conan recipe — git-who 1.3 (Go project)

git-who is a CLI tool for answering "who wrote this code" in Git repos,
like git blame for file trees. Pure Go, statically linked.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class GitWhoConan(ConanFile):
    name = "git-who"
    version = "1.3"
    description = "Git blame for file trees — who wrote this code?"
    license = "MIT"
    homepage = "https://github.com/sinclairtarget/git-who"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    # Go projects don't use C/C++ build layouts; no layout() needed.

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R26: CGO_ENABLED=0 produces statically-linked binary
        ldflags = "-X main.version=v1.3"
        self.run(
            "cd \"%s\" && CGO_ENABLED=0 go build -ldflags \"-s -w %s\" -o git-who ."
            % (self.source_folder, ldflags),
        )

    def package(self):
        copy(self, "git-who", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
