#!/usr/bin/env python3
"""Conan recipe — buildifier 8.0.3 (Go project).

buildifier is a Go tool from bazelbuild/buildtools for formatting Bazel BUILD files.
Build system: Go (go build), not Autotools.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BuildifierConan(ConanFile):
    name = "buildifier"
    version = "8.0.3"
    description = "Bazel BUILD file formatter and linter"
    license = "MIT"
    homepage = "https://github.com/bazelbuild/buildtools"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # No Autotools/CMake — Go build uses environment variables
        pass

    def build(self):
        apply_conandata_patches(self)

        # Set up Go environment using os.environ for reliability
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

        # Run go build from source folder where ./buildifier subdirectory exists
        # Use external linker to avoid mmap issues on HMDFS
        output_bin = os.path.join(self.build_folder, "buildifier")
        self.run(
            f'"{go_bin}" build -ldflags="-s -w -X main.buildVersion=8.0.3 -X main.buildScmRevision=v8.0.3 -linkmode=external" '
            f'-o "{output_bin}" ./buildifier',
            cwd=self.source_folder,
        )

    def package(self):
        # Copy the built binary
        copy(self, "buildifier", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # buildifier is an executable tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
