#!/usr/bin/env python3
"""Conan recipe for unfurl 0.4.3 — pull out bits of URLs provided on stdin.

unfurl is a Go CLI tool (tomnomnom/unfurl) that extracts components from URLs
(scheme, domain, path, query keys/values, etc.) fed via stdin, with a
printf-style custom format engine. It is a standalone executable — no
linkable library.

Build system: custom (Go toolchain cross-compiled for HarmonyOS aarch64)
Product: `unfurl` executable
Dependencies: none at build time (Go modules vendored by go build)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class UnfurlConan(ConanFile):
    name = "unfurl"
    version = "0.4.3"
    description = "unfurl — pull out bits of URLs provided on stdin"
    license = "MIT"
    homepage = "https://github.com/tomnomnom/unfurl"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # HarmonyOS aarch64 交叉编译: Go 1.22+ 支持 GOOS=ohos GOARCH=arm64
        env = dict(os.environ)
        if self.settings.os == "OHOS":
            env["GOOS"] = "ohos"
            env["GOARCH"] = "arm64"
            env.setdefault("CGO_ENABLED", "0")
        self.run("go build -trimpath -ldflags '-s -w' -o unfurl .", env=env)

    def package(self):
        copy(self, "unfurl", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # unfurl 是独立 CLI 工具, 无可链接库/头文件
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
