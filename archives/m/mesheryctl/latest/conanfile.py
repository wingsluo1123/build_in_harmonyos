#!/usr/bin/env python3
"""Conan recipe — mesheryctl (Meshery CLI tool, Go project).

mesheryctl is the command-line interface for Meshery, the cloud native
management plane. It is written in Go and built with `go build`.

Source: https://github.com/meshery/meshery (mesheryctl subdirectory)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MesheryctlConan(ConanFile):
    name = "mesheryctl"
    version = "latest"
    description = "Meshery CLI tool — command-line interface for the cloud native management plane"
    license = "Apache-2.0"
    homepage = "https://meshery.io"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: OHOS platform compatibility check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mesheryctl is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Locate the Go binary
        go_bin = shutil.which("go")
        if not go_bin:
            # Try harmonybrew
            harmonybrew_go = os.path.expanduser("~/.harmonybrew/bin/go")
            if os.path.isfile(harmonybrew_go):
                go_bin = harmonybrew_go
            else:
                raise ConanInvalidConfiguration(
                    "Go compiler not found. Install Go via: "
                    "curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- go"
                )

        # Determine target architecture
        go_arch = "arm64" if str(self.settings.arch) in ("armv8", "aarch64", "arm64") else "amd64"

        # Build mesheryctl binary
        ldflags = (
            "-w -s "
            "-X github.com/meshery/meshery/mesheryctl/internal/cli/root/constants.version=v1.0.52 "
            "-X github.com/meshery/meshery/mesheryctl/internal/cli/root/constants.commitsha=unknown "
            "-X github.com/meshery/meshery/mesheryctl/internal/cli/root/constants.releasechannel=edge"
        )

        # Build from source folder where go.mod is located
        build_dir = os.path.join(self.source_folder, "bin")
        os.makedirs(build_dir, exist_ok=True)

        self.run(
            f'CGO_ENABLED=0 GOARCH={go_arch} GOOS=linux GO111MODULE=on '
            f'GOPROXY=https://goproxy.cn,direct GONOSUMDB=* '
            f'{go_bin} build -ldflags="{ldflags}" '
            f'-o bin/mesheryctl mesheryctl/cmd/mesheryctl/main.go',
            cwd=self.source_folder
        )

    def package(self):
        copy(self, "mesheryctl", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        bin_path = os.path.join(self.package_folder, "bin")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
