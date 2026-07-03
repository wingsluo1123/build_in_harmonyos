#!/usr/bin/env python3
"""Conan recipe for hysteria (Go-based proxy/VPN tool).

Hysteria is a Go project using go.work workspace with modules in app/, core/, extras/.
The main entry point is app/main.go. Build uses `go build` with CGO_ENABLED=0.

R32: validate() checks os in ("Linux", "OHOS")
R1:  export_sources() calls export_conandata_patches()
R26: Not applicable (Go static binary, no system shared libs)
R27: No Conan dependencies (Go modules handled by go.mod)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class HysteriaConan(ConanFile):
    name = "hysteria"
    version = "latest"
    description = "Hysteria is a feature-packed proxy & relay tool optimized for lossy, unstable connections"
    license = "Apache-2.0"
    homepage = "https://github.com/apernet/hysteria"
    url = "https://github.com/apernet/hysteria"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        # R32: OHOS platform compatibility check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"hysteria only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _find_go(self):
        """Find the Go binary. Check PATH, then harmonybrew, then fail."""
        go = shutil.which("go")
        if go:
            return go
        # Check harmonybrew
        harmonybrew_go = os.path.expanduser("~/.harmonybrew/bin/go")
        if os.path.isfile(harmonybrew_go) and os.access(harmonybrew_go, os.X_OK):
            return harmonybrew_go
        raise ConanInvalidConfiguration(
            "Go compiler not found. Install Go (e.g., via harmonybrew or cmd-pkgs)."
        )

    def build(self):
        apply_conandata_patches(self)
        go = self._find_go()

        # Go environment as list of strings (Conan 2.x requirement)
        go_env = [
            "CGO_ENABLED=0",
            "GOPROXY=https://goproxy.cn,direct",
            "GONOSUMCHECK=1",
            "GONOSUMDB=*",
            "GOFLAGS=-insecure",
        ]

        # Build ldflags for version embedding
        ldflags = " ".join([
            "-X", "github.com/apernet/hysteria/app/v2/cmd.appVersion=2.9.3",
            "-X", "github.com/apernet/hysteria/app/v2/cmd.appType=release",
            "-s", "-w",
        ])

        # Build the binary
        self.run(
            f'"{go}" build -o hysteria -ldflags "{ldflags}" -trimpath ./app',
            env=go_env,
        )

    def package(self):
        # Copy the binary to the package
        copy(self, "hysteria", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        # Make it executable
        bin_path = os.path.join(self.package_folder, "bin", "hysteria")
        if os.path.isfile(bin_path):
            os.chmod(bin_path, 0o755)

    def package_info(self):
        # This is a binary tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Add bin to PATH
        self.cpp_info.bindirs = ["bin"]
