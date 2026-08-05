#!/usr/bin/env python3
"""Conan 2.x recipe — csvq 1.18.1

csvq is a command-line tool that provides SQL-like query language for CSV files.
It is written in Go and uses `go build` for compilation.

Build system: Go (go build)
Product type: application (command-line tool)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class CsvqConan(ConanFile):
    name = "csvq"
    version = "1.18.1"
    description = "SQL-like query language for CSV files (Go implementation)"
    license = "MIT"
    homepage = "https://github.com/mithrandie/csvq"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Go build environment — set via os.environ (R33: no bare shell vars)
        os.environ["CGO_ENABLED"] = "0"
        os.environ["GOOS"] = "linux"
        os.environ["GOARCH"] = "arm64"
        os.environ["GOPROXY"] = "https://goproxy.cn,direct"
        os.environ["GOFLAGS"] = "-mod=mod"
        # Build csvq binary using Go
        self.run(
            "go build -tags urfave_cli_no_docs -trimpath "
            '-ldflags="-X github.com/mithrandie/csvq/lib/query.Version=v1.18.1 -s -w" '
            "-o csvq ."
        )

    def package(self):
        copy(self, "csvq", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
