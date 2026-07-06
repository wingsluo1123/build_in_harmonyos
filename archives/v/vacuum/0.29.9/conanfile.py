#!/usr/bin/env python3
"""Conan recipe — vacuum 0.29.9 (Go project)

vacuum is the world's fastest OpenAPI, AsyncAPI and JSON Schema linter,
written in Go. This recipe builds a statically-linked binary for OHOS.

R26: Go produces statically-linked binaries by default (CGO_ENABLED=0).
R27: No external Conan dependencies — all Go modules managed by go mod.
R32: settings.os supports both "Linux" and "OHOS".
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class VacuumConan(ConanFile):
    name = "vacuum"
    version = "0.29.9"
    description = "The world's fastest OpenAPI, AsyncAPI and JSON Schema linter"
    license = "MIT"
    homepage = "https://github.com/daveshanley/vacuum"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Pure Go project — all dependencies managed by go mod
        pass

    # Go projects don't use C/C++ build layouts; no layout() needed.

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R26: CGO_ENABLED=0 produces statically-linked binary
        ldflags = "-X main.version=v0.29.9 -X main.commit=conan-build -X main.date=2026-07-06"
        # Use build_folder — Conan copies sources here, go.mod lives here
        self.run(
            "cd \"%s\" && CGO_ENABLED=0 go build -ldflags \"-s -w %s\" -o bin/vacuum ."
            % (self.build_folder, ldflags),
        )

    def package(self):
        # Binary was created in build_folder/bin/vacuum
        # Conan copy() with pattern preserves relative path, so copy from bin/ subdir
        copy(self, "vacuum", src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # vacuum is a CLI tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
