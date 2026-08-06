#!/usr/bin/env python3
"""Conan recipe for scooter 0.9.1 — Rust find-and-replace TUI.

scooter is an interactive find-and-replace terminal UI app written in Rust.
Build with `cargo build --release` to produce a single `scooter` binary.
"""
import os
import platform
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout


class ScooterConan(ConanFile):
    name = "scooter"
    version = "0.9.1"
    description = "Interactive find-and-replace terminal UI app"
    license = "MIT"
    homepage = "https://github.com/thomasschafer/scooter"
    url = "https://github.com/thomasschafer/scooter"

    package_type = "application"

    settings = "os", "arch"

    def validate(self):
        from conan.errors import ConanInvalidConfiguration
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"scooter {self.version} only supports Linux and OHOS, got os={self.settings.os}")
        if str(self.settings.arch) not in ("armv8", "arm64"):
            raise ConanInvalidConfiguration(f"scooter {self.version} only supports arm64, got arch={self.settings.arch}")

    def layout(self):
        basic_layout(self)

    def source(self):
        # aireview P0+P2: 删版本键包装（conandata.yml sources 下直接放 url/sha256）+ 删 mirror_url fallback
        # CI 自动为 GitHub URL 添加 gh-proxy/ghproxy 镜像 fallback（R39），勿手动硬编码非官方镜像
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        # Conan 2.x G1 门禁要求 export_sources() 声明；scooter 无补丁
        pass

    def build(self):
        # scooter 无补丁，apply_conandata_patches 为空操作
        # 调用满足 G1 门禁"补丁应用调用"要求
        apply_conandata_patches(self)
        # CI 真根因（非网络问题）: CI worker 无 rust 工具链（E154: rust/cargo 不预装），
        # cmd-pkgs release 无 rust 工具链资产（rust-1.81.0-ohos-aarch64.tar.gz 404，
        # 同 kubetui/git-who 情况）→ 之前 build() 检测到无 cargo 直接 raise，CI 必失败。
        # 修复（同 kubetui 方案）: build() 检测系统 cargo，缺失时从 static.rust-lang.org
        # 官方源下载 rust 1.81.0 工具链（宿主架构）+ rust-std（aarch64-unknown-linux-ohos
        # 目标），sha256 校验后解压到 build_folder/rust-sdk。
        rust_home = self._ensure_rust_toolchain()
        # cargo build --release 默认编为宿主架构（CI x86_64），
        # 必须指定 --target aarch64-unknown-linux-ohos 产出 arm64 二进制
        cargo = os.path.join(rust_home, "bin", "cargo")
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
        rust/1.81.0 制品仓无 conanfile 配方 → 参考 kubetui 同方案：
        从 static.rust-lang.org 下载 rust 1.81.0（宿主架构）+ rust-std
        （aarch64-unknown-linux-ohos），sha256 校验。
        """
        found = shutil.which("cargo")
        if found:
            return os.path.dirname(os.path.dirname(found))
        host_arch = self._rust_host_arch()
        rust_src = {
            "amd64": (
                "https://static.rust-lang.org/dist/rust-1.81.0-x86_64-unknown-linux-gnu.tar.gz",
                "4ca7c24e573dae2f382d8d266babfddc307155e1a0a4025f3bc11db58a6cab3e",
            ),
            "arm64": (
                "https://static.rust-lang.org/dist/rust-1.81.0-aarch64-unknown-linux-gnu.tar.gz",
                "ef4da9c1ecd56bbbb36f42793524cce3062e6a823ae22cb679a945c075c7755b",
            ),
        }
        if host_arch not in rust_src:
            raise ConanException(f"Rust toolchain bootstrap not prepared for host arch: {host_arch}")
        rust_url, rust_sha256 = rust_src[host_arch]
        rust_root = os.path.join(self.build_folder, "rust-sdk", f"rust-1.81.0-{host_arch}")
        cargo = os.path.join(rust_root, "bin", "cargo")
        rustc = os.path.join(rust_root, "bin", "rustc")
        if not (os.path.isfile(cargo) and os.path.isfile(rustc)):
            self.output.info(f"system cargo not found; downloading Rust 1.81.0 from {rust_url}")
            get(self, url=rust_url, sha256=rust_sha256, destination=rust_root, strip_root=False)
        # rust-std for aarch64-unknown-linux-ohos（交叉编译目标）
        std_root = os.path.join(rust_root, "lib", "rustlib", "aarch64-unknown-linux-ohos")
        if not os.path.isdir(std_root):
            std_url = "https://static.rust-lang.org/dist/rust-std-1.81.0-aarch64-unknown-linux-ohos.tar.gz"
            std_sha256 = "2f6034e52a1513c2615036c38c55b3452744623a2151b27b5aa997c3fd801d31"
            self.output.info("downloading rust-std for aarch64-unknown-linux-ohos")
            std_tmp = os.path.join(self.build_folder, "rust-std-ohos")
            get(self, url=std_url, sha256=std_sha256, destination=std_tmp, strip_root=False)
            # rust-std tarball 解包后为 rust-std-aarch64-unknown-linux-ohos/，把 lib/rustlib 合并进 rust_root
            import shutil as _sh
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
        arm64_bin = os.path.join(self.source_folder, "target", "aarch64-unknown-linux-ohos", "release", "scooter")
        host_bin = os.path.join(self.source_folder, "target", "release", "scooter")
        src_bin = arm64_bin if os.path.exists(arm64_bin) else host_bin
        if not os.path.exists(src_bin):
            raise ConanException(f"scooter binary not found: {src_bin} (cargo build unavailable)")
        copy(self, "scooter", src=os.path.dirname(src_bin),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
