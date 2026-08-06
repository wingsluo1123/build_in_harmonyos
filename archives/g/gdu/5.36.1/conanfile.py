#!/usr/bin/env python3
"""Conan recipe — gdu 5.36.1 (Go/custom build system)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GduConan(ConanFile):
    name = "gdu"
    version = "5.36.1"
    description = "Fast disk usage analyzer with console interface"
    license = "MIT"
    homepage = "https://github.com/dundee/gdu"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Go build environment
        # CGO_ENABLED=0: pure Go static binary, no C dependencies
        os.environ["CGO_ENABLED"] = "0"
        # GOPROXY: use mirror accessible from HarmonyOS network
        os.environ["GOPROXY"] = "https://goproxy.cn,direct"
        os.environ["GOSUMDB"] = "off"

        # HarmonyOS: Go linker requires mmap-compatible filesystem for output
        # tmpfs (default TMPDIR) does not support mmap ACCESS_WRITE
        hmfs_path = "/data/storage/el2/base/haps/entry/files"
        if os.path.isdir(hmfs_path):
            os.environ["TMPDIR"] = hmfs_path
            os.environ["GOCACHE"] = os.path.join(hmfs_path, "go-cache")
            os.environ["GOPATH"] = os.path.join(hmfs_path, "go-path")

        output_dir = os.path.join(self.build_folder, "dist")
        os.makedirs(output_dir, exist_ok=True)

        # Build flags:
        # -trimpath: remove file system paths from binary
        # -mod=mod: allow downloading Go modules
        # No -buildmode=pie: PIE binaries conflict with ELF signing on HarmonyOS
        ldflags = (
            "-s -w -extldflags '-static' "
            "-X 'github.com/dundee/gdu/v5/build.Version=v5.36.1' "
            "-X 'github.com/dundee/gdu/v5/build.Time=2026-08-06' "
            "-X 'github.com/dundee/gdu/v5/build.User=ohos-builder'"
        )

        self.run(
            f"go build -trimpath -mod=mod -modcacherw "
            f'-ldflags="{ldflags}" '
            f"-o {output_dir}/gdu "
            f"github.com/dundee/gdu/v5/cmd/gdu"
        )

    def package(self):
        copy(self, "gdu", os.path.join(self.build_folder, "dist"),
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
