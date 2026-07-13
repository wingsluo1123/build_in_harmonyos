#!/usr/bin/env python3
"""Conan recipe for gofumpt — Go CLI tool (formatting).

gofumpt is a Go CLI tool, not a C/C++ library.
Uses custom Go build (CGO_ENABLED=0 static).

CI environment must have Go available in PATH (Go 1.25+).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
import os


class GofumptConan(ConanFile):
    name = "gofumpt"
    version = "0.10.0-r0"
    description = "A stricter gofmt, written in Go"
    license = "MIT"
    homepage = "https://github.com/mvdan/gofumpt"
    url = "https://github.com/mvdan/gofumpt"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.output.info("Building gofumpt with Go...")
        # Use /data/storage/el2/base/cache (hmfs) to avoid HMDFS mmap restrictions
        self.run("CGO_ENABLED=0 GOOS=linux GOARCH=arm64 "
                 "GOPROXY=https://goproxy.cn,direct "
                 "TMPDIR=/data/storage/el2/base/cache "
                 "go build -ldflags='-s -w' -o /data/storage/el2/base/cache/gofumpt .")
        copy(self, "/data/storage/el2/base/cache/gofumpt", src="", dst=self.build_folder)

    def package(self):
        copy(self, "gofumpt", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
