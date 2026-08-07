#!/usr/bin/env python3
"""Conan recipe for kubetui 1.14.0 — Rust TUI tool.

kubetui is a Terminal User Interface tool for real-time monitoring
and exploration of Kubernetes resources, written in Rust.
Build with `cargo build --release` to produce a single binary.
"""
import os
import platform
import shutil

from conan import ConanFile
from conan.errors import ConanException
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
        # R39: 仅用官方源（github.com/sarub0b0/kubetui）。CI 有内置 GitHub 镜像
        # fallback（gh-proxy/ghproxy/gitclone/moeyy/kkgithub）处理 GitHub 不可达，
        # 配方内不再自定义 mirror_url（aireview Critical: gitcode.com 非官方源 +
        # sha256=None 跳过校验属供应链投毒风险，同 groonga/inotify-tools 处理）。
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        # Conan 2.x G1 门禁要求 export_sources() 声明；kubetui 无补丁
        pass

    def build(self):
        # kubetui 无补丁，apply_conandata_patches 为空操作
        # 调用满足 G1 门禁"补丁应用调用"要求
        apply_conandata_patches(self)
        # CI 真根因（非网络问题）: CI worker 无 rust 工具链（E154: rust/cargo 不预装），
        # cmd-pkgs release 无 rust 工具链资产（rust-1.81.0-ohos-aarch64.tar.gz 404，
        # 同 git-who 的 go 情况）→ 之前 build() 检测到无 cargo 直接 raise，CI 必失败。
        # 修复（同 git-who 下载 go SDK 方案）: build() 检测系统 cargo，缺失时从
        # static.rust-lang.org 官方源下载 rust 1.81.0 工具链（宿主架构）+ rust-std
        # （aarch64-unknown-linux-ohos 目标），sha256 校验后解压到 build_folder/rust-sdk。
        rust_home = self._ensure_rust_toolchain()
        # cargo build --release 默认编为宿主架构（CI x86_64），
        # 必须指定 --target aarch64-unknown-linux-ohos 产出 arm64 二进制
        cargo = os.path.join(rust_home, "bin", "cargo")
        rustc = os.path.join(rust_home, "bin", "rustc")
        ret = self.run(
            f'PATH={os.path.join(rust_home, "bin")}:$PATH '
            f'RUSTUP_HOME={rust_home} '
            f'CARGO_HOME={os.path.join(self.build_folder, "cargo-home")} '
            f'"{cargo}" build --release --target aarch64-unknown-linux-ohos '
            f'--config target.aarch64-unknown-linux-ohos.linker=clang',
            cwd=self.source_folder, env="conanbuild",
        )
        if ret != 0:
            raise ConanException(f"cargo build failed with exit code {ret}")

    def _ensure_rust_toolchain(self):
        """Locate a usable cargo; fall back to downloading the official Rust toolchain.

        CI worker 无系统 rust（E154），cmd-pkgs 无 rust 工具链资产（404），
        rust/1.81.0 制品仓无 conanfile 配方 → 参考 git-who 16.4.1 的 go SDK 方案：
        从 static.rust-lang.org 下载 rust 1.81.0（宿主架构）+ rust-std
        （aarch64-unknown-linux-ohos），sha256 校验。

        CI #14730: 完整 rust-1.81.0 工具链 tarball 488MB，下载在 3600s 超时限制
        内仅完成 2% → 改下组件包（rustc/cargo/rust-std，总量约 210MB），
        解包到统一 rust_root 后 cargo/rustc 均在 rust_root/bin 下。
        """
        found = shutil.which("cargo")
        if found:
            return os.path.dirname(os.path.dirname(found))
        host_arch = self._rust_host_arch()
        # 组件包（triple 按宿主架构；比完整 rust-*.tar.gz 小一半以上）。
        # CI #15412: static.rust-lang.org 对 CI worker 下载极慢（45 分钟超时内
        # rustc 164.5MB 仅下载 10%）→ USTC 镜像优先（实测可达 200），官方兜底。
        triple = "x86_64-unknown-linux-gnu" if host_arch == "amd64" else "aarch64-unknown-linux-gnu"
        rustc_sha256 = (
            "08acb66f6cfc3d44d06c349edf947f41f30bb9fc74a28b0f003ad2d6fa96e878"
            if host_arch == "arm64"
            else "13f9d5cec8b8613074d0e021d967840a162c6d7e1534c6e577e1c2b1b60d2775"
        )
        components = {
            "rustc": (
                [
                    f"https://mirrors.ustc.edu.cn/rust-static/dist/rustc-1.81.0-{triple}.tar.gz",
                    f"https://static.rust-lang.org/dist/rustc-1.81.0-{triple}.tar.gz",
                ],
                rustc_sha256,
            ),
            "cargo": (
                [
                    f"https://mirrors.ustc.edu.cn/rust-static/dist/cargo-1.81.0-{triple}.tar.gz",
                    f"https://static.rust-lang.org/dist/cargo-1.81.0-{triple}.tar.gz",
                ],
                "00c5185b49a885df529832327d2584a9c26dd03df64f0a52b32a3f34bf3498c1",
            ),
            # 宿主 rust-std 已内嵌在 rustc 组件包中（lib/rustlib/<host>/），无需单独下载；
            # 交叉编译目标 aarch64-unknown-linux-ohos 的 rust-std 在下方单独获取。
            # 删除冗余宿主 rust-std 下载（CI #15526: 工具链下载量过大致 3600s 超时）
        }
        rust_root = os.path.join(self.build_folder, "rust-sdk", f"rust-1.81.0-{host_arch}")
        cargo = os.path.join(rust_root, "bin", "cargo")
        rustc = os.path.join(rust_root, "bin", "rustc")
        import shutil as _sh
        if not (os.path.isfile(cargo) and os.path.isfile(rustc)):
            for comp_name, (comp_urls, comp_sha256) in components.items():
                comp_tmp = os.path.join(self.build_folder, f"rust-comp-{comp_name}")
                if os.path.isdir(os.path.join(comp_tmp, "bin")):
                    continue
                self.output.info(f"downloading {comp_name} 1.81.0 from {comp_urls[0]}")
                get(self, url=comp_urls, sha256=comp_sha256, destination=comp_tmp, strip_root=False)
                # 组件包解包后为 {comp_name}-1.81.0-{triple}/，把 bin/ lib/ 合并进 rust_root
                for dirpath, dirnames, filenames in os.walk(comp_tmp):
                    rel = os.path.relpath(dirpath, comp_tmp)
                    parts = rel.split(os.sep)
                    if parts and parts[0] in ("bin", "lib", "share", "etc"):
                        target_dir = os.path.join(rust_root, *parts)
                        os.makedirs(target_dir, exist_ok=True)
                        for fn in filenames:
                            src_f = os.path.join(dirpath, fn)
                            dst_f = os.path.join(target_dir, fn)
                            if not os.path.exists(dst_f):
                                _sh.copy2(src_f, dst_f)
        # rust-std for aarch64-unknown-linux-ohos（交叉编译目标）
        std_root = os.path.join(rust_root, "lib", "rustlib", "aarch64-unknown-linux-ohos")
        if not os.path.isdir(std_root):
            std_url = "https://static.rust-lang.org/dist/rust-std-1.81.0-aarch64-unknown-linux-ohos.tar.gz"
            std_sha256 = "2f6034e52a1513c2615036c38c55b3452744623a2151b27b5aa997c3fd801d31"
            self.output.info(f"downloading rust-std for aarch64-unknown-linux-ohos")
            std_tmp = os.path.join(self.build_folder, "rust-std-ohos")
            get(self, url=std_url, sha256=std_sha256, destination=std_tmp, strip_root=False)
            # rust-std tarball 解包后为 rust-std-aarch64-unknown-linux-ohos/，把 lib/rustlib 合并进 rust_root
            for dirpath, dirnames, filenames in os.walk(std_tmp):
                rel = os.path.relpath(dirpath, std_tmp)
                parts = rel.split(os.sep)
                if "rustlib" in parts:
                    idx = parts.index("rustlib")
                    target_dir = os.path.join(rust_root, *parts[idx:])
                    os.makedirs(target_dir, exist_ok=True)
                    for fn in filenames:
                        src_f = os.path.join(dirpath, fn)
                        dst_f = os.path.join(target_dir, fn)
                        if not os.path.exists(dst_f):
                            _sh.copy2(src_f, dst_f)
        if not (os.path.isfile(cargo) and os.path.isfile(rustc)):
            raise ConanException(f"Rust toolchain download failed: {cargo} not found")
        return rust_root

    @staticmethod
    def _rust_host_arch():
        machine = platform.machine().lower()
        return {
            "aarch64": "arm64",
            "arm64": "arm64",
            "x86_64": "amd64",
            "amd64": "amd64",
        }.get(machine, machine)

    def package(self):
        # P1: 删占位假二进制分支，只复制真实产物（aireview: 欺骗性打包）
        # P2: copy() src 改目录非文件路径（aireview: src 传文件路径导致真实二进制打包失败）
        arm64_bin = os.path.join(self.source_folder, "target", "aarch64-unknown-linux-ohos", "release", "kubetui")
        host_bin = os.path.join(self.source_folder, "target", "release", "kubetui")
        src_bin = arm64_bin if os.path.exists(arm64_bin) else host_bin
        if not os.path.exists(src_bin):
            raise ConanException(f"kubetui binary not found: {src_bin} (cargo build unavailable)")
        copy(self, "kubetui", src=os.path.dirname(src_bin),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
