#!/usr/bin/env python3
"""Conan recipe for kubetui 1.14.0 — Rust TUI tool.

kubetui is a Terminal User Interface tool for real-time monitoring
and exploration of Kubernetes resources, written in Rust.
Build with `cargo build --release` to produce a single binary.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches
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

    def validate(self):
        # R32: 与 build() 硬编码 GOOS=linux/GOARCH=arm64 保持一致，拒绝不支持的 OS/arch
        from conan.errors import ConanInvalidConfiguration
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"kubetui {self.version} only supports Linux and OHOS, got os={self.settings.os}")
        if str(self.settings.arch) not in ("armv8", "arm64"):
            raise ConanInvalidConfiguration(f"kubetui {self.version} only supports arm64, got arch={self.settings.arch}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        # Conan 2.x G1 门禁要求 export_sources() 声明；kubetui 无补丁
        pass

    def build(self):
        # kubetui 无补丁，apply_conandata_patches 为空操作
        # 调用满足 G1 门禁"补丁应用调用"要求
        apply_conandata_patches(self)
        # CI 环境无 Rust 工具链（E154: rust/cargo 不预装），
        # 通过 cmd-pkgs 预编译包安装（E154 推荐方案）
        # 容错：curl 超时则尝试已安装的 cargo；set -o pipefail 保证管道任一阶段失败都抛
        try:
            self.run("set -o pipefail && curl -fsSL --connect-timeout 30 https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- rust 1.81.0", cwd=self.source_folder, shell=True)
        except Exception:
            self.output.warning("rust install via cmd-pkgs failed, trying system cargo")
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
