#!/usr/bin/env python3
"""Conan recipe template — Makefile projects (SCAFFOLD, AI must adjust).

⚠️  This is a SCAFFOLD only. Makefile projects vary widely — each has different
    configure scripts, build targets, output names, and install rules.
    AI MUST review and adjust every method below before use.

Typical Makefile project types:
  1. Raw make (no configure, e.g. bzip2) — build() runs make directly
  2. Makefile + configure (e.g. zlib) — build() runs ./configure first, then make

Key rules:
  - R9:  Use make -j1 (not -j$(nproc))
  - R26: System-name libs (zlib, ncurses, etc.) must be static-only
  - R5:  Use CONFIG_SHELL for configure scripts (OHOS has no /bin/sh)
  -      Set env: os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

Usage: Replace Buildah, buildah, 1.44.0, buildah 1.44.0, MIT,
       Fill in requires(), build commands, and cpp_info.libs as needed.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BuildahConan(ConanFile):
    name = "buildah"
    version = "1.44.0"
    description = "buildah 1.44.0"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("go/1.25.8@ohpcd/stable")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Set up Go environment for buildah (Go project using Makefile)
        goroot = "/storage/Users/currentUser/usr/local/go1263"
        go_bin = os.path.join(goroot, "bin", "go")
        gopath = os.path.join(os.path.expanduser("~"), "go")

        os.environ["GOROOT"] = goroot
        os.environ["GOPATH"] = gopath
        os.environ["GOPROXY"] = "https://goproxy.cn,direct"
        os.environ["CGO_ENABLED"] = "0"
        os.environ["GOOS"] = "linux"
        os.environ["GOARCH"] = "arm64"
        os.environ["TMPDIR"] = os.path.expanduser("~/tmp")
        os.environ["GOCACHE"] = os.path.join(os.path.expanduser("~"), ".cache", "go-build")
        os.environ["GOMODCACHE"] = os.path.join(gopath, "pkg", "mod")
        os.environ["PATH"] = goroot + "/bin:/data/service/hnp/bin:" + os.environ.get("PATH", "")

        # Build using Makefile (patches fix entrypoint_arm64.gz for arm64)
        self.run("make -j1 GOCACHE=" + os.environ["GOCACHE"] + " GOMODCACHE=" + os.environ["GOMODCACHE"])

    def package(self):
        # Copy the built binary
        copy(self, "buildah", os.path.join(self.build_folder, "bin"),
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
