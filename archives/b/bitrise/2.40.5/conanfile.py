#!/usr/bin/env python3
"""Conan recipe — Go projects (go build).

Bitrise runner CLI - Mobile CI/CD automation tool.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BitriseConan(ConanFile):
    name = "bitrise"
    version = "2.40.5"
    description = "Bitrise runner CLI - Mobile CI/CD automation tool"
    license = "MIT"
    homepage = "https://github.com/bitrise-io/bitrise"
    url = ""  # CI fills this

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Set up Go environment
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

        self.run(
            f'"{go_bin}" build -ldflags '
            "'-X github.com/bitrise-io/bitrise/v2/version.VERSION=2.40.5' "
            "-o bitrise-bin ."
        )

    def package(self):
        copy(self, "bitrise-bin", self.build_folder,
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
