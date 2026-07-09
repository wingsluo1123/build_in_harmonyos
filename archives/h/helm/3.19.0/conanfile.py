#!/usr/bin/env python3
"""Conan recipe for helm 3.19.0 — Go project (go build).

helm is a Kubernetes package manager written in Go.
This recipe builds the helm CLI binary using `go build`.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class HelmConan(ConanFile):
    name = "helm"
    version = "3.19.0"
    description = "The Kubernetes Package Manager: Think of it like apt/yum/homebrew for Kubernetes."
    license = "Apache-2.0"
    homepage = "https://helm.sh"
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
        # Run from source_folder since basic_layout copies sources there
        self.run(f"cd {self.source_folder} && CGO_ENABLED=0 go build -trimpath -ldflags '-w -s' -o bin/helm ./cmd/helm")

    def package(self):
        copy(self, "helm", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["helm"]
