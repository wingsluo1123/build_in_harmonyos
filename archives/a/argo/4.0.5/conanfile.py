#!/usr/bin/env python3
"""Conan 2.x recipe — Argo Workflows CLI 4.0.5

Argo Workflows is a Kubernetes-native workflow engine.
This recipe builds the `argo` CLI binary using the Go toolchain.

Build system: Go (custom)
Output: single static binary (argo)
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ArgoConan(ConanFile):
    name = "argo"
    version = "4.0.5"
    description = "Argo Workflows CLI — Kubernetes-native workflow engine command-line tool"
    license = "Apache-2.0"
    homepage = "https://github.com/argoproj/argo-workflows"
    url = ""  # CI fills this

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

    def build(self):
        apply_conandata_patches(self)

        # Create UI placeholder for go:embed dist/app
        ui_dist = os.path.join(self.source_folder, "ui", "dist", "app")
        os.makedirs(ui_dist, exist_ok=True)
        if not os.path.exists(os.path.join(ui_dist, "index.html")):
            with open(os.path.join(ui_dist, "index.html"), "w") as f:
                f.write("<!DOCTYPE html><html><head><title>Argo</title></head><body>Argo UI placeholder</body></html>")

        # Go environment for HarmonyOS/OpenHarmony — set in os.environ directly
        os.environ["CGO_ENABLED"] = "0"
        os.environ["GOOS"] = "linux"
        os.environ["GOARCH"] = "arm64"
        os.environ["GOPROXY"] = "https://goproxy.cn,direct"
        os.environ["GOTOOLCHAIN"] = "local"

        # Go linker mmap fails on HMDFS — output to ext2 partition
        ext2_tmp = "/data/storage/el2/base/haps/entry/files"
        if os.path.isdir(ext2_tmp):
            os.environ["TMPDIR"] = ext2_tmp
            os.environ["GOCACHE"] = os.path.join(ext2_tmp, "go-build-cache")
            output_path = os.path.join(ext2_tmp, "argo")
        else:
            output_path = os.path.join(self.build_folder, "argo")

        # Download Go modules (run from source folder where go.mod lives)
        self.run("go mod download", cwd=self.source_folder)

        # Build argo CLI binary
        build_date = "2026-08-05T00:00:00Z"
        ldflags = (
            "-s -w "
            "-X github.com/argoproj/argo-workflows/v4.version=v4.0.5 "
            f"-X github.com/argoproj/argo-workflows/v4.buildDate={build_date} "
            "-X github.com/argoproj/argo-workflows/v4.gitTreeState=clean "
            "-extldflags -static"
        )
        self.run(
            f'go build -ldflags "{ldflags}" -o {output_path} ./cmd/argo',
            cwd=self.source_folder
        )

        # Copy binary to build folder for packaging
        if output_path != os.path.join(self.build_folder, "argo"):
            shutil.copy2(output_path, os.path.join(self.build_folder, "argo"))

    def package(self):
        copy(self, "argo", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
