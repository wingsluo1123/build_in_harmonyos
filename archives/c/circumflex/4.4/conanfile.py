#!/usr/bin/env python3
"""Conan recipe for circumflex 4.4 (Go CLI - Hacker News terminal browser).

circumflex is a pure Go project (no CGO), so this recipe uses go build
instead of CMake/Autotools. It is a terminal tool (static binary).

Rules enforced:
  - R32: settings.os in ("Linux", "OHOS") for platform checks
  - R27: @ohpcd/stable for dependencies (none for pure Go)
  - R28: test_package/ required
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class CircumflexConan(ConanFile):
    name = "circumflex"
    version = "4.4"
    description = "Terminal Hacker News browser with Vim-style navigation, syntax highlighting, and Reader Mode"
    license = "MIT"
    homepage = "https://github.com/bensadeh/circumflex"
    url = "https://github.com/bensadeh/circumflex"

    settings = "os", "compiler", "build_type", "arch"

    # Go projects don't need C/C++ compilers
    # Pure Go (CGO_ENABLED=0) - no system libs needed

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Go build - no CGO, static binary
        # GOPROXY set for Chinese mirror (goproxy.cn)
        os.environ["CGO_ENABLED"] = "0"
        os.environ["GOOS"] = "linux"
        os.environ["GOARCH"] = "arm64"
        os.environ["GOPROXY"] = "https://goproxy.cn,direct"
        # Go build must run from the source directory (module root with go.mod)
        src = self.source_folder
        self.run(f"go build -ldflags=\"-s -w\" -o {src}/clx ./cmd/clx", cwd=src)

    def package(self):
        copy(self, "clx", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Go binary - no libs to expose
        self.cpp_info.libs = []
        # Add bin to PATH
        self.cpp_info.bindirs = ["bin"]
