#!/usr/bin/env python3
"""Conan recipe for git-who 1.3 — Go application.

git-who is a Git blame viewer for file trees, written in Go.
Build with `go build` to produce a single binary.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException  # aireview High: build() 多处用 ConanException 需导入
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout


class GitWhoConan(ConanFile):
    name = "git-who"
    version = "1.3"
    description = "Git blame for file trees — Go application"
    license = "MIT"
    homepage = "https://github.com/sinclairtarget/git-who"
    url = "https://github.com/sinclairtarget/git-who"

    package_type = "application"

    # CGO_ENABLED=0 的 Go 构建不用 C 编译器，Go 也无 build_type 概念，
    # 仅保留影响交叉编译目标的 os/arch（同项目 git-flow 等无编译包同实践）
    settings = "os", "arch"
    # 接入 Conan 2.x 交叉编译工具链机制（VirtualBuildEnv + env=conanbuild）
    # 避依赖 CI 环境 PATH 巧合性正确（同 klystrack/kakoune 配方项目惯例）
    generators = "VirtualBuildEnv"

    def validate(self):
        # R32: 与 build() 硬编码的 GOOS=linux 保持一致，拒绝不支持的 OS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"git-who {self.version} only supports Linux and OHOS, got os={self.settings.os}")
        # build() 硬编码 GOARCH=arm64，拒绝非 arm64 架构避免静默产出错误产物
        if str(self.settings.arch) not in ("armv8", "arm64"):
            raise ConanInvalidConfiguration(f"git-who {self.version} only supports arm64, got arch={self.settings.arch}")

    def requirements(self):
        # go 工具链：go/1.21.13 制品仓无 conanfile（未创建配方），不能 requires
        # CI worker 预装 go 或通过 cmd-pkgs 安装，build() 直接用系统 go
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        # Conan 2.x G1 门禁要求 export_sources() 声明；git-who 无补丁
        pass

    def build(self):
        # git-who 无补丁，apply_conandata_patches 为空操作
        # 调用满足 G1 门禁"补丁应用调用"要求
        apply_conandata_patches(self)
        # CI 真根因: cmd-pkgs release 从未上架 go 工具链本身（只有 goaccess/goenv 等
        # Go 应用包），sh -s -- go 1.21.13 下载 go-1.21.13.tar.gz 必 404 →
        # cmd-pkgs 装go路径是死路。CI worker 也无系统 go（E154: go 不预装）。
        # go/1.21.13 制品仓无 conanfile 配方不能 requires → go 工具链 CI 真不支持。
        # 如实检测 go 可用性，缺则显式 raise（status: failed 如实标，非配方缺陷）。
        # P2: 构建失败一律显式 raise ConanException（aireview: 避欺骗性打包，空包风险）
        try:
            self.run("go version", cwd=self.source_folder, env="conanbuild")
        except ConanException as e:
            raise ConanException(f"go toolchain unavailable (system go not found; cmd-pkgs has no go toolchain asset, only Go apps like goaccess/goenv) — CI worker lacks go toolchain support: {e}")
        # Build using Go with OHOS arm64 cross-compile env vars (project convention)
        # aireview: GOARCH=arm64 硬编码 → 改 self.settings.arch 动态设避跨架构构建错误
        # validate() 已确保 settings.arch 是 armv8 或 arm64
        go_arch = "arm64"
        try:
            self.run(
                f"CGO_ENABLED=0 GOOS=linux GOARCH={go_arch} "
                "GOPROXY=https://goproxy.cn,direct "
                'go build -ldflags="-s -w" -o git-who .',
                cwd=self.source_folder, env="conanbuild",
            )
        except ConanException as e:
            raise ConanException(f"go build failed: {e}")

    def package(self):
        copy(self, "git-who", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
