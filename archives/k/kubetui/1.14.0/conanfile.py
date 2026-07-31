#!/usr/bin/env python3
"""Conan recipe for kubetui 1.14.0 — Rust TUI tool.

kubetui is a Terminal User Interface tool for real-time monitoring
and exploration of Kubernetes resources, written in Rust.
Build with `cargo build --release` to produce a single binary.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class KubetuiConan(ConanFile):
    name = "kubetui"
    version = "1.14.0"
    description = "TUI tool for real-time monitoring Kubernetes resources"
    license = "MIT"
    homepage = "https://github.com/sarub0b0/kubetui"
    url = "https://github.com/sarub0b0/kubetui"

    package_type = "application"

    settings = "os", "arch"

    def build_requirements(self):
        # CI 环境无 Rust 工具链，依赖 rust/cargo 工具链包（同 hurl/ripgrep 等 Rust 项目）
        self.tool_requires("rust/1.95.0")
        self.tool_requires("cargo/1.95.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Rust 工具链通过 cmd-pkgs 预编译包安装（E154 知识条目）
        # cargo build --release 默认编为宿主架构（CI x86_64），
        # 必须指定 --target aarch64-unknown-linux-ohos 产出 arm64 二进制
        self.run("cargo build --release --target aarch64-unknown-linux-ohos", cwd=self.source_folder)

    def package(self):
        copy(self, "kubetui",
             src=os.path.join(self.source_folder, "target", "aarch64-unknown-linux-ohos", "release"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
