#!/usr/bin/env python3
"""Conan recipe for actionlint 1.7.9 — Go project (go build).

actionlint is a static checker for GitHub Actions workflow files.
This recipe builds the actionlint CLI binary using `go build`.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class ActionlintConan(ConanFile):
    name = "actionlint"
    version = "1.7.9"
    description = "A static checker for GitHub Actions workflow files"
    license = "MIT"
    homepage = "https://github.com/rhysd/actionlint"
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
        self.run(
            "cd {src} && CGO_ENABLED=0 go build -trimpath "
            "-ldflags '-s -w -X github.com/rhysd/actionlint.version=1.7.9' "
            "-o bin/actionlint ./cmd/actionlint".format(src=self.source_folder)
        )

    def package(self):
        copy(self, "actionlint", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["actionlint"]
