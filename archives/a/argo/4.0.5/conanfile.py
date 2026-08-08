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
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class ArgoConan(ConanFile):
    name = "argo"
    version = "4.0.5"
    description = "Argo Workflows CLI — Kubernetes-native workflow engine command-line tool"
    license = "Apache-2.0"
    homepage = "https://github.com/argoproj/argo-workflows"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"argo supports Linux and OHOS only, got {self.settings.os}"
            )

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
        env.vars(self).save_script("conanbuild")

    def build(self):
        apply_conandata_patches(self)

        # Ensure Go toolchain is available
        go_bin = self._ensure_go_toolchain()

        # Set writable TMPDIR on OHOS (/tmp is read-only, E002)
        # Go linker uses mmap which fails on HMDFS
        ext2_dir = "/data/storage/el2/base/haps/entry/files"
        if os.path.isdir(ext2_dir):
            os.environ["TMPDIR"] = ext2_dir
            os.environ["GOCACHE"] = os.path.join(ext2_dir, "go-build-cache")
            os.environ["GOMODCACHE"] = os.path.join(ext2_dir, "go-mod-cache")
            os.makedirs(os.environ["GOCACHE"], exist_ok=True)
            os.makedirs(os.environ["GOMODCACHE"], exist_ok=True)

        # Create UI placeholder for go:embed dist/app
        ui_dist = os.path.join(self.source_folder, "ui", "dist", "app")
        os.makedirs(ui_dist, exist_ok=True)
        if not os.path.exists(os.path.join(ui_dist, "index.html")):
            with open(os.path.join(ui_dist, "index.html"), "w") as f:
                f.write("<!DOCTYPE html><html><head><title>Argo</title></head><body>Argo UI placeholder</body></html>")

        # Determine output path — use build folder or ext2 partition
        output_path = os.path.join(
            os.environ.get("TMPDIR", self.build_folder), "argo"
        )

        # Download Go modules (run from source folder where go.mod lives)
        self.run(f'"{go_bin}" mod download', env="conanbuild", cwd=self.source_folder)

        # Build argo CLI binary
        ldflags = (
            "-s -w "
            "-X github.com/argoproj/argo-workflows/v4.version=v4.0.5 "
            "-X github.com/argoproj/argo-workflows/v4.buildDate=2026-08-09T00:00:00Z "
            "-X github.com/argoproj/argo-workflows/v4.gitCommit=0ab1452144d8f4d57c50b37ce50dad218868e950 "
            "-X github.com/argoproj/argo-workflows/v4.gitTreeState=clean "
            "-extldflags -static"
        )
        self.run(
            f'"{go_bin}" build -ldflags "{ldflags}" -o "{output_path}" ./cmd/argo',
            env="conanbuild",
            cwd=self.source_folder,
        )

        # Copy built binary to build folder for packaging
        if os.path.exists(output_path):
            shutil.copy2(output_path, os.path.join(self.build_folder, "argo"))

    def _ensure_go_toolchain(self):
        """Ensure Go toolchain is available, install via Harmonybrew if needed."""
        go_path = shutil.which("go")
        if go_path:
            return go_path

        brew_go = os.path.expanduser("~/.harmonybrew/bin/go")
        if os.path.isfile(brew_go):
            os.environ["PATH"] = (
                os.path.dirname(brew_go) + ":" + os.environ.get("PATH", "")
            )
            return brew_go

        brew_bin = os.path.expanduser("~/.harmonybrew/bin/brew")
        if not os.path.isfile(brew_bin):
            self.run(
                'zsh -c "$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)"',
                env="conanbuild",
            )

        self.run(f'"{brew_bin}" install go', env="conanbuild")

        brew_bin_dir = os.path.expanduser("~/.harmonybrew/bin")
        os.environ["PATH"] = brew_bin_dir + ":" + os.environ.get("PATH", "")
        return os.path.join(brew_bin_dir, "go")

    def package(self):
        copy(self, "argo", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
