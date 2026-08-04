#!/usr/bin/env python3
"""Conan 2.x recipe — Argo Workflows CLI 4.0.5

Argo Workflows is a Kubernetes-native workflow engine.
This recipe builds the `argo` CLI binary using the Go toolchain.

Build system: Go (custom)
Output: single static binary (argo)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class ArgoConan(ConanFile):
    name = "argo"
    version = "4.0.5"
    description = "Argo Workflows CLI — Kubernetes-native workflow engine command-line tool"
    license = "Apache-2.0"
    homepage = "https://github.com/argoproj/argo-workflows"

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Go toolchain is a system dependency, not a Conan package.
        # Go module dependencies are managed by go.mod via GOPROXY.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Use Conan Environment to set Go build variables (R33 compliant)
        env = Environment()
        env.define("CGO_ENABLED", "0")
        env.define("GOOS", "linux")
        env.define("GOARCH", "arm64")
        env.define("GOPROXY", "https://goproxy.cn,direct")
        env.define("GOTOOLCHAIN", "local")
        # Go linker mmap may fail on some filesystems; use Conan's TMPDIR
        # which is already set by the profile/build environment.
        env.vars(self).save_script("conanbuild")

    def build(self):
        apply_conandata_patches(self)

        # Create UI placeholder for go:embed dist/app
        ui_dist = os.path.join(self.source_folder, "ui", "dist", "app")
        os.makedirs(ui_dist, exist_ok=True)
        if not os.path.exists(os.path.join(ui_dist, "index.html")):
            with open(os.path.join(ui_dist, "index.html"), "w") as f:
                f.write("<!DOCTYPE html><html><head><title>Argo</title></head><body>Argo UI placeholder</body></html>")

        # Determine output path — use build folder by default
        output_path = os.path.join(self.build_folder, "argo")

        # Download Go modules (run from source folder where go.mod lives)
        self.run("go mod download", cwd=self.source_folder)

        # Build argo CLI binary
        ldflags = (
            "-s -w "
            "-X github.com/argoproj/argo-workflows/v4.version=v4.0.5 "
            "-X github.com/argoproj/argo-workflows/v4.buildDate=2026-08-05T00:00:00Z "
            "-X github.com/argoproj/argo-workflows/v4.gitTreeState=clean "
            "-extldflags -static"
        )
        self.run(
            f'go build -ldflags "{ldflags}" -o {output_path} ./cmd/argo',
            cwd=self.source_folder
        )

    def package(self):
        copy(self, "argo", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
