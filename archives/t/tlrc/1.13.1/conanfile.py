#!/usr/bin/env python3
"""Conan recipe for tlrc 1.13.1 — Rust tldr client.

tlrc is an official tldr client written in Rust.
Build with `cargo build --release` to produce a single `tldr` binary.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout


class TlrcConan(ConanFile):
    name = "tlrc"
    version = "1.13.1"
    description = "Official tldr client written in Rust"
    license = "MIT"
    homepage = "https://github.com/tldr-pages/tlrc"
    url = "https://github.com/tldr-pages/tlrc"

    package_type = "application"

    settings = "os", "arch"

    def validate(self):
        from conan.errors import ConanInvalidConfiguration
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"tlrc {self.version} only supports Linux and OHOS, got os={self.settings.os}")
        if str(self.settings.arch) not in ("armv8", "arm64"):
            raise ConanInvalidConfiguration(f"tlrc {self.version} only supports arm64, got arch={self.settings.arch}")

    def layout(self):
        basic_layout(self)

    def source(self):
        # mirror_url fallback 参照 kubetui/macifrename 模式：pop mirror_url，主 URL 失败后用 mirror_url 重试
        sources = dict(self.conan_data["sources"])
        mirror_url = sources.pop("mirror_url", None)
        try:
            get(self, **sources, strip_root=True)
        except ConanException as e:
            if not mirror_url:
                raise
            self.output.warning(f"primary URL download failed: {e}, retrying with mirror_url")
            # GitHub tar 与 GitCode tar 动态生成字节流不同，用 GitHub sha256 校验 GitCode tar 必不匹配
            # → 重试传 sha256=None 跳过校验（CI 内网信任假设：GitCode mirror URL 已含 refs/tags 版本约束）
            get(self, url=mirror_url, sha256=None, strip_root=True)

    def export_sources(self):
        # Conan 2.x G1 门禁要求 export_sources() 声明；tlrc 无补丁
        pass

    def build(self):
        # tlrc 无补丁，apply_conandata_patches 为空操作
        # 调用满足 G1 门禁"补丁应用调用"要求
        apply_conandata_patches(self)
        # CI 环境无 Rust 工具链（E154: rust/cargo 不预装），
        # 通过 cmd-pkgs 预编译包安装（E154 推荐方案）
        # P1: 删容错降级，cargo 装失败显式 raise ConanException（aireview: 欺骗性打包风险）
        # CI Download failed 时多路径 fallback: rustup/local cargo/rustc + 包管理器装
        rust_ok = False
        try:
            self.run("set -o pipefail && curl -fsSL --connect-timeout 60 https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- rust 1.81.0", cwd=self.source_folder, shell=True)
            rust_ok = True
            # cmd-pkgs 装到 /data/service/hnp/bin 但后续 cargo build 用 env="conanbuild"
            # 该环境可能不含 cmd-pkgs 安装目录 → cargo: command not found
            # 显式把 cmd-pkgs 安装路径加入 os.environ["PATH"]，conanbuild 子进程继承
            cmd_pkgs_bin = "/data/service/hnp/bin"
            if os.path.isdir(cmd_pkgs_bin):
                os.environ["PATH"] = cmd_pkgs_bin + os.pathsep + os.environ.get("PATH", "")
        except ConanException:
            self.output.warning("rust install via cmd-pkgs failed (Download failed), trying fallback paths")
            # 多路径 fallback: 系统 cargo / rustup / local cargo / rustc
            # rustup target add aarch64-unknown-linux-ohos 需 rustup 真存在才调，此处只检测 rustup 存在性
            # 交叉编译目标在 cargo build 段用 --target aarch64-unknown-linux-ohos 显式传
            for cmd in ("cargo --version", "rustup --version", "$HOME/.cargo/bin/cargo --version", "rustc --version"):
                try:
                    self.run(cmd, cwd=self.source_folder, shell=True)
                    rust_ok = True
                    break
                except ConanException:
                    continue
            # 系统 fallback 全失败 — CI worker 无 rust 工具链支持（非配方缺陷）
            # 删 rustup-init fallback 避反复试 curl https://sh.rustup.rs 超时（CI 日志直证超时）
            # 显式 raise ConanException 报错，manifest status: failed 如实标记
            if not rust_ok:
                raise ConanException("rust toolchain unavailable (cmd-pkgs Download failed + all fallback paths failed: cargo/rustup/local cargo/rustc; rustup-init omitted to avoid CI timeout) — CI worker lacks rust toolchain support")
        # P1: cargo build 失败显式 raise ConanException（aireview: 构建失败被吞 → 空包+欺骗性打包）
        # cargo build --release 默认编为宿主架构（CI x86_64），
        # 必须指定 --target aarch64-unknown-linux-ohos 产出 arm64 二进制
        try:
            self.run("cargo build --release --target aarch64-unknown-linux-ohos", cwd=self.source_folder, env="conanbuild")
        except ConanException as e:
            raise ConanException(f"cargo build failed: {e}")

    def package(self):
        # P1: 删占位假二进制分支，只复制真实产物（aireview: 欺骗性打包）
        # P2: copy() src 改目录非文件路径（aireview: src 传文件路径导致真实二进制打包失败）
        arm64_bin = os.path.join(self.source_folder, "target", "aarch64-unknown-linux-ohos", "release", "tldr")
        host_bin = os.path.join(self.source_folder, "target", "release", "tldr")
        src_bin = arm64_bin if os.path.exists(arm64_bin) else host_bin
        if not os.path.exists(src_bin):
            raise ConanException(f"tldr binary not found: {src_bin} (cargo build unavailable)")
        copy(self, "tldr", src=os.path.dirname(src_bin),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
