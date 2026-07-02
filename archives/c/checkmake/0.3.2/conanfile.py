#!/usr/bin/env python3
"""Conan recipe — checkmake 0.3.2 (Go project, Make build system).

checkmake is a linter/analyzer for Makefiles, written in Go.
Build system: Go + Make (make binaries target).
The binary is statically compiled — no runtime dependencies.

Cross-compiles with CGO_ENABLED=0 for OHOS aarch64.
"""
import os
import subprocess
from datetime import datetime, timezone

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class CheckmakeConan(ConanFile):
    name = "checkmake"
    version = "0.3.2"
    description = "Linter/analyzer for Makefiles"
    license = "MIT"
    homepage = "https://github.com/checkmake/checkmake"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # Go compiler path (harmonybrew installed)
    go_root = "/storage/Users/currentUser/.harmonybrew/Cellar/go/1.26.4_4/libexec"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies; Go binary is statically compiled.
        pass

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS"
            )

    def layout(self):
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        go_bin = os.path.join(self.go_root, "bin", "go")

        # Replicate the Makefile's ldflags for version info injection.
        # Use Python datetime instead of subprocess (date not in Conan PATH).
        buildtime = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        builder = "OpenDesk <opendesk@ohos.dev>"

        # Get go version string
        go_path = os.path.join(self.go_root, "bin") + ":" + os.environ.get("PATH", "")
        try:
            goversion = subprocess.check_output(
                [go_bin, "version"],
                env={"PATH": go_path, "GOROOT": self.go_root}
            ).decode().strip()
        except Exception:
            goversion = "go1.26.4 linux/arm64"

        ldflags = (
            f"-X 'main.version=0.3.2' "
            f"-X 'main.buildTime={buildtime}' "
            f"-X 'main.builder={builder}' "
            f"-X 'main.goversion={goversion}'"
        )

        # Set Go build environment variables directly (bypass Makefile's
        # shell spawning which loses PATH in Conan's build env).
        # Conan's self.run() env param must be a list of "KEY=VALUE" strings.
        env_list = [
            f"CGO_ENABLED=0",
            f"GOOS=linux",
            f"GOARCH=arm64",
            f"GOROOT={self.go_root}",
            f"GOPROXY=https://goproxy.cn,direct",
            f"GOFLAGS=-mod=mod",
            f"GO111MODULE=on",
            f"TMPDIR={os.environ.get('TMPDIR', '/storage/Users/currentUser/tmp')}",
            f"PATH={go_path}",
        ]

        # Build the checkmake binary directly with go build.
        self.run(
            f'"{go_bin}" build -trimpath '
            f'-ldflags="{ldflags}" '
            f'-o checkmake cmd/checkmake/main.go',
            env=env_list,
        )

    def package(self):
        copy(self, "checkmake", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # checkmake is a standalone CLI binary, not a library.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
