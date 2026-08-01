#!/usr/bin/env python3
"""Conan recipe for unfurl 0.4.3 — pull out bits of URLs provided on stdin.

unfurl is a Go CLI tool (tomnomnom/unfurl) that extracts components from URLs
(scheme, domain, path, query keys/values, etc.) fed via stdin, with a
printf-style custom format engine. It is a standalone executable — no
linkable library.

Build system: custom (Go toolchain, static build via CGO_ENABLED=0)
Product: `unfurl` executable
Dependencies: none at build time (Go modules fetched by go build)
"""
import os
import shutil
from glob import glob

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import get, copy, chdir
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

    # Conan arch -> GOARCH。HarmonyOS PC 为 aarch64, 对应 armv8/arm64。
    _GOARCH = {"armv8": "arm64", "arm64": "arm64", "x86_64": "amd64"}

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _find_go(self):
        """定位 Go 工具链。

        HarmonyOS 环境下 go 未必在 profile 的 PATH 中, 仓库既有 Go 包
        (buildifier / amass / arduino-cli 等) 统一使用 ~/usr/local/go1263。
        注意: Go 1.26.0 的 HarmonyOS 二进制存在 corrupted 问题, 需 1.26.3+。
        """
        found = shutil.which("go")
        if found:
            return found
        for candidate in sorted(glob(os.path.expanduser("~/usr/local/go*/bin/go")),
                                reverse=True):
            if os.access(candidate, os.X_OK):
                return candidate
        raise ConanException(
            "未找到 Go 工具链: PATH 中无 go, 且 ~/usr/local/go*/bin/go 不存在。"
            " unfurl 为纯 Go 项目, 需 Go 1.22+ (HarmonyOS 建议 1.26.3)。")

    def _go_env(self, go_exe, tmp_dir):
        """构建 Go 环境变量。

        R33: 用 Conan 的 Environment 注入, 不把 dict 传给 self.run(env=...) ——
        self.run 的 env 形参接收的是环境脚本名, 传 dict 会直接抛 TypeError。
        """
        env = Environment()
        goroot = os.path.dirname(os.path.dirname(go_exe))
        env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.join(goroot, "bin"))
        # HarmonyOS 基于 Linux 内核, 标准 Go 工具链没有 ohos 目标;
        # 全仓库已验证路径为 GOOS=linux + CGO_ENABLED=0 静态链接。
        env.define("GOOS", "linux")
        env.define("GOARCH", self._GOARCH.get(str(self.settings.arch), "arm64"))
        env.define("CGO_ENABLED", "0")
        # 国内镜像, 避免 proxy.golang.org 不可达导致依赖拉取超时。
        # unfurl 有 3 个外部 module 依赖 (Cgboal/DomainParser、jakewarren/tldomains、
        # golang.org/x/net indirect), 构建期必须能拉取。
        env.define("GOPROXY", "https://goproxy.cn,direct")
        # 不设 GOFLAGS=-mod=mod: 上游 go.sum 完整, 默认 readonly 即可, 且
        # no_copy_source=True 时 source_folder 是共享缓存, 应避免写入。
        # 默认 /tmp 在 HarmonyOS 上空间有限, 落到 Conan 构建目录更稳
        env.define("GOTMPDIR", tmp_dir)
        return env

    def build(self):
        go_exe = self._find_go()
        output = os.path.join(self.build_folder, "unfurl")
        tmp_dir = os.path.join(self.build_folder, ".gotmp")
        os.makedirs(tmp_dir, exist_ok=True)

        # no_copy_source=True + basic_layout 会把 source_folder 与 build_folder
        # 分开, 而 go.mod / *.go 都在 source_folder, 必须 chdir 过去构建,
        # 否则 go build 会在空目录里报 "no Go files in ..."。
        with self._go_env(go_exe, tmp_dir).vars(self).apply():
            with chdir(self, self.source_folder):
                if not self.conf.get("tools.build:skip_test", default=False,
                                     check_type=bool):
                    # 上游官方单测 TestFormat (format_test.go, 32 条用例)
                    self.run(f'"{go_exe}" test ./...')
                self.run(f'"{go_exe}" build -trimpath -ldflags "-s -w"'
                         f' -o "{output}" .')

        if not os.path.isfile(output):
            raise ConanException(f"go build 未产出可执行文件: {output}")

    def package(self):
        copy(self, "unfurl", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # unfurl 是独立 CLI 工具, 无可链接库/头文件
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
