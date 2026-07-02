#!/usr/bin/env python3
"""Conan recipe — checkmake 0.3.2 (Go project, Make build system).

checkmake is a linter/analyzer for Makefiles, written in Go.
Build system: Go + Make (make binaries target).
The binary is statically compiled — no runtime dependencies.

Cross-compiles with CGO_ENABLED=0 for OHOS aarch64.
"""
import os
import shutil
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

    def _find_go(self):
        """Dynamically discover a working Go binary and its GOROOT.

        Tries PATH first, then common OHOS/Harmonybrew locations.
        Each candidate is verified by actually running `go env GOROOT`.
        This avoids hardcoding environment-specific paths (R18).
        """
        candidates = []

        # Try PATH first
        path_go = shutil.which("go")
        if path_go:
            candidates.append(path_go)

        # Fallback: common locations on OHOS/Harmonybrew
        for path in [
            "/usr/local/bin/go",
            "/data/service/hnp/bin/go",
            os.path.expanduser("~/.harmonybrew/bin/go"),
            os.path.expanduser("~/usr/local/bin/go"),
        ]:
            if path not in candidates and os.path.isfile(path):
                candidates.append(path)

        for go_bin in candidates:
            try:
                result = subprocess.run(
                    [go_bin, "env", "GOROOT"],
                    capture_output=True, text=True, timeout=10,
                    env={"PATH": os.path.dirname(go_bin) + ":" + os.environ.get("PATH", "")},
                )
                if result.returncode == 0:
                    go_root = result.stdout.strip()
                    if go_root:
                        return go_bin, go_root
            except Exception:
                continue

        raise ConanInvalidConfiguration(
            "Go compiler not found or not executable. "
            "Install Go and ensure it is accessible via PATH."
        )

    def build(self):
        apply_conandata_patches(self)
        go_bin, go_root = self._find_go()

        # Replicate the Makefile's ldflags for version info injection.
        # Use Python datetime instead of subprocess (date not in Conan PATH).
        buildtime = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        builder = "OpenDesk <opendesk@ohos.org>"

        # Get go version string
        go_path = os.path.join(go_root, "bin") + ":" + os.environ.get("PATH", "")
        try:
            goversion = subprocess.check_output(
                [go_bin, "version"],
                env={"PATH": go_path, "GOROOT": go_root}
            ).decode().strip()
        except Exception:
            goversion = "go (unknown version)"

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
            f"GOROOT={go_root}",
            f"GOPROXY=https://goproxy.cn,direct",
            f"GOFLAGS=-mod=mod",
            f"GO111MODULE=on",
            f"TMPDIR={os.environ.get('TMPDIR', os.path.expanduser('~/tmp'))}",
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
