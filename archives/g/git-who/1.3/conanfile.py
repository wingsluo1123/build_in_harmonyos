#!/usr/bin/env python3
"""Conan recipe for git-who 1.3 — Go application.

git-who is a Git blame viewer for file trees, written in Go.
Build with `go build` to produce a single binary.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class GitWhoConan(ConanFile):
    name = "git-who"
    version = "1.3"
    description = "Git blame for file trees — Go application"
    license = "MIT"
    homepage = "https://github.com/sinclairtarget/git-who"
    url = "https://github.com/sinclairtarget/git-who"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Build using Go with OHOS arm64 cross-compile env vars (project convention)
        self.run(
            "CGO_ENABLED=0 GOOS=linux GOARCH=arm64 "
            "GOPROXY=https://goproxy.cn,direct "
            "go build -ldflags=\"-s -w\" -o git-who .",
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "git-who", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
