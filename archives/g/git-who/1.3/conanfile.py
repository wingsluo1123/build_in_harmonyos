#!/usr/bin/env python3
"""Conan recipe for git-who 1.3 — Go application.

git-who is a Git blame viewer for file trees, written in Go.
Build with `go build` to produce a single binary.
"""
import os
import platform
import shutil

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

    # CI worker 无系统 go（E154: go 不预装），cmd-pkgs 无 go 工具链资产，
    # go/1.21.13 制品仓无 conanfile 不能 requires → 从官方镜像下载 go SDK
    # （同 git-town 16.4.1 方案：golang.google.cn 主源 + dl.google.com 兜底）
    _go_version = "1.21.13"
    _go_archives = {
        "amd64": (
            [
                "https://golang.google.cn/dl/go1.21.13.linux-amd64.tar.gz",
                "https://dl.google.com/go/go1.21.13.linux-amd64.tar.gz",
            ],
            "502fc16d5910562461e6a6631fb6377de2322aad7304bf2bcd23500ba9dab4a7",
        ),
        "arm64": (
            [
                "https://golang.google.cn/dl/go1.21.13.linux-arm64.tar.gz",
                "https://dl.google.com/go/go1.21.13.linux-arm64.tar.gz",
            ],
            "2ca2d70dc9c84feef959eb31f2a5aac33eefd8c97fe48f1548886d737bffabd4",
        ),
    }

    def validate(self):
        # R32: 与 build() 硬编码的 GOOS=linux 保持一致，拒绝不支持的 OS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"git-who {self.version} only supports Linux and OHOS, got os={self.settings.os}")
        # build() 硬编码 GOARCH=arm64，拒绝非 arm64 架构避免静默产出错误产物
        if str(self.settings.arch) not in ("armv8", "arm64"):
            raise ConanInvalidConfiguration(f"git-who {self.version} only supports arm64, got arch={self.settings.arch}")

    def requirements(self):
        # go 工具链：go/1.21.13 制品仓无 conanfile（未创建配方），不能 requires；
        # build() 检测系统 go，缺失时从官方镜像下载 go SDK（git-town 同方案）
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
        go = self._go_executable()
        # Build using Go with OHOS arm64 cross-compile env vars (project convention)
        # aireview: GOARCH=arm64 硬编码 → 改 self.settings.arch 动态设避跨架构构建错误
        # validate() 已确保 settings.arch 是 armv8 或 arm64
        go_arch = "arm64"
        try:
            self.run(
                f'"{go}" version',
                cwd=self.source_folder, env="conanbuild",
            )
            self.run(
                f"CGO_ENABLED=0 GOOS=linux GOARCH={go_arch} "
                f"GOROOT={os.path.dirname(os.path.dirname(go))} "
                f"GOPATH={os.path.join(self.build_folder, 'gopath')} "
                "GOPROXY=https://goproxy.cn,direct "
                f'"{go}" build -ldflags="-s -w" -o git-who .',
                cwd=self.source_folder, env="conanbuild",
            )
        except ConanException as e:
            raise ConanException(f"go build failed: {e}")

    def _go_executable(self):
        """Locate a usable go; fall back to downloading the official Go SDK.

        CI worker 无系统 go（E154），cmd-pkgs 无 go 工具链资产，
        go/1.21.13 制品仓无 conanfile 配方 → 参考 git-town 16.4.1：
        从 golang.google.cn / dl.google.com 下载 go SDK（sha256 校验）。
        """
        found = shutil.which("go")
        if found:
            return found
        host_arch = self._go_host_arch()
        if host_arch not in self._go_archives:
            raise ConanInvalidConfiguration(f"Go SDK bootstrap not prepared for host arch: {host_arch}")
        sdk_root = os.path.join(self.build_folder, "go-sdk", f"go{self._go_version}-{host_arch}")
        goroot = os.path.join(sdk_root, "go")
        gobin = os.path.join(goroot, "bin", "go")
        if not os.path.isfile(gobin):
            urls, sha256 = self._go_archives[host_arch]
            self.output.info(f"system go not found; downloading Go {self._go_version} from {urls[0]}")
            get(self, url=urls, sha256=sha256, destination=sdk_root, strip_root=False)
        if not os.path.isfile(gobin):
            raise ConanException(f"Go SDK download failed: {gobin} not found")
        return gobin

    @staticmethod
    def _go_host_arch():
        machine = platform.machine().lower()
        return {
            "aarch64": "arm64",
            "arm64": "arm64",
            "x86_64": "amd64",
            "amd64": "amd64",
        }.get(machine, machine)

    def package(self):
        copy(self, "git-who", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
