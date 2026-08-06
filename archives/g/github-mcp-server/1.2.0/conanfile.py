#!/usr/bin/env python3
"""Conan 2.x recipe — github-mcp-server 1.2.0

GitHub MCP Server connects AI tools directly to GitHub's platform.
This is a Go project built with `go build` (CGO_ENABLED=0 static binary).

Build produces two executables:
  - github-mcp-server (main MCP server)
  - mcpcurl (helper HTTP client for MCP)

R27: No external Conan dependencies (Go modules are self-contained).
R28: test_package/ included.
R34: test_package executes the binary (--version).
R38: commands.json declared at software level.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class GithubMcpServerConan(ConanFile):
    name = "github-mcp-server"
    version = "1.2.0"
    description = "GitHub MCP Server - connects AI tools directly to GitHub's platform"
    license = "MIT"
    homepage = "https://github.com/github/github-mcp-server"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Go project with CGO_ENABLED=0 — no C/C++ dependencies.
        # Go modules are managed by go.mod, not Conan.
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Verify Go toolchain is available; install if missing
        go_bin = shutil.which("go")
        if not go_bin or not os.path.isfile(go_bin):
            # Try common HarmonyOS Go locations
            for candidate in [
                os.path.expanduser("~/.harmonybrew/bin/go"),
                "/data/service/hnp/bin/go",
            ]:
                if os.path.isfile(candidate):
                    go_bin = candidate
                    break
            else:
                # Go not found — install via Harmonybrew
                self.output.info("Go toolchain not found, installing via Harmonybrew...")
                brew = shutil.which("brew") or os.path.expanduser("~/.harmonybrew/bin/brew")
                if brew and os.path.isfile(brew):
                    self.run(f'"{brew}" install go')
                else:
                    # Install Harmonybrew first, then Go
                    self.run(
                        'zsh -c "$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)" || true'
                    )
                    brew = os.path.expanduser("~/.harmonybrew/bin/brew")
                    if os.path.isfile(brew):
                        self.run(f'"{brew}" install go')

                # Re-check after installation
                go_bin = shutil.which("go") or os.path.expanduser("~/.harmonybrew/bin/go")
                if not go_bin or not os.path.isfile(go_bin):
                    raise RuntimeError(
                        "Go toolchain installation failed. "
                        "Install Go manually: brew install go"
                    )

        # Map Conan settings to Go environment
        # OHOS maps to linux for Go cross-compilation
        goos = "linux"  # OHOS uses Linux kernel
        goarch = "arm64" if self.settings.arch == "armv8" else str(self.settings.arch)

        # Set up Go build environment (R33: use os.environ, not shell vars in self.run)
        # Resolve symlink to find actual GOROOT
        go_bin_real = os.path.realpath(go_bin)
        goroot = os.path.dirname(os.path.dirname(go_bin_real))
        gopath = os.path.join(self.build_folder, "gopath")
        os.makedirs(gopath, exist_ok=True)

        os.environ["GOROOT"] = goroot
        os.environ["GOPATH"] = gopath
        os.environ["GOPROXY"] = "https://goproxy.cn,direct"
        os.environ["CGO_ENABLED"] = "0"
        os.environ["GOOS"] = goos
        os.environ["GOARCH"] = goarch
        # Ensure Go binary directory is in PATH
        go_bin_dir = os.path.dirname(go_bin)
        if go_bin_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = go_bin_dir + ":" + os.environ.get("PATH", "")

        # Download Go module dependencies
        self.run(f'go mod download', cwd=self.source_folder)

        # Build main binary: github-mcp-server
        self.run(
            f'go build -ldflags '
            f'"-X main.version=1.2.0 -X main.commit=v1.2.0" '
            f'-o {os.path.join(self.build_folder, "github-mcp-server")} '
            f'./cmd/github-mcp-server/',
            cwd=self.source_folder,
        )

        # Build helper binary: mcpcurl
        self.run(
            f'go build '
            f'-o {os.path.join(self.build_folder, "mcpcurl")} '
            f'./cmd/mcpcurl/',
            cwd=self.source_folder,
        )

        # NOTE: Do NOT strip binaries — HarmonyOS MAC security rejects
        # stripped ELF binaries with "Operation not permitted".
        # Go static binaries are larger but functional without stripping.

    def package(self):
        # Copy compiled binaries to package bin/
        for binary in ["github-mcp-server", "mcpcurl"]:
            src = os.path.join(self.build_folder, binary)
            if os.path.isfile(src):
                copy(self, binary, self.build_folder,
                     os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
