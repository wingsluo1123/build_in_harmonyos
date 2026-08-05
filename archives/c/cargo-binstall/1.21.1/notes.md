# cargo-binstall 1.21.1 Conan 适配笔记

## 编译环境
- 构建系统: precompiled (Rust musl static binary from GitHub releases)
- 编译日期: 2026-08-05
- 编译器: N/A (precompiled binary — rustc SIGSEGV on HarmonyOS)
- 状态: published

## 背景

cargo-binstall 是一个 Rust 工具，用于从 GitHub releases 等源安装 Rust 预编译二进制文件。
由于 rustc（Rust 编译器）在 HarmonyOS 上崩溃（SIGSEGV），无法从源码编译。
因此使用上游 GitHub releases 中的 `aarch64-unknown-linux-musl` 静态二进制。

### 历史适配

- 之前已有 homebrew 适配（v1.19.1），使用预编译二进制方式，但无 conan 配方
- 本次适配：创建完整 conan 配方（conanfile.py + conandata.yml + test_package/）
- 版本升级至 v1.21.1（上游 2026-07-25 发布）

## 编译步骤

### 预编译方案（rustc 在 HarmonyOS 上崩溃，无法从源码编译）

1. **下载预编译二进制**: 从 GitHub releases 下载 `cargo-binstall-aarch64-unknown-linux-musl.full.tgz` (v1.21.1)
   - 包含: cargo-binstall, detect-targets, detect-wasi 三个 ELF 二进制
   - SHA256: 1dcc18f75bfc51d96b65206a0eedaee322c65316d4b1de15f2173a579747f090
   - 通过 ghfast.top GitHub 代理下载（直连 GitHub SSL 证书验证失败）

2. **ELF 签名**: 使用 binary-sign-tool sign -selfSign 1 对三个二进制签名
   - 需先 objcopy --remove-section .codesign 清理旧签名段
   - 签名后二进制可在 HarmonyOS 上正常执行

3. **验证结果**:
   ```bash
   $ cargo-binstall -V
   1.21.1

   $ detect-targets
   aarch64-unknown-linux-musl

   $ detect-wasi
   WASI is not runnable
   ```

   所有三个二进制均正常工作。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | rustc SIGSEGV on HarmonyOS | HarmonyOS kernel 不完全兼容 Rust 编译器 | 使用 GitHub releases 预编译 musl 静态二进制 |
| 2 | GitHub 直连 SSL 证书验证失败 | 鸿蒙缺少 CA 证书 | 安装 CA 证书到 /storage/Users/currentUser/usr/local/ssl/cert.pem + ghfast.top 代理 |
| 3 | 二进制 Permission denied | ELF 未签名 | binary-sign-tool sign -selfSign 1 签名 |
| 4 | rustup 无法安装 Rust 工具链 | rustup 不识别 HarmonyOS OS 类型 | 使用预编译方案绕过 |

## 依赖版本

- 无编译依赖（预编译二进制）
- 运行时依赖: musl libc (系统自带 /lib/ld-musl-aarch64.so.1)

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cargo-binstall | ~15MB | Rust binary installer 主程序 |
| detect-targets | ~573KB | 目标平台检测辅助程序 |
| detect-wasi | ~377KB | WASI运行时检测辅助程序 |

## Conan 配方说明

- **package_type**: application（命令行工具）
- **build()**: 无编译步骤，仅对 HarmonyOS 执行 ELF 签名
- **package()**: 复制三个二进制到 bin/，附带 LICENSE 和 README.md
- **package_info()**: bindirs=["bin"]，无库文件
- **package_id()**: 移除 compiler 和 build_type 依赖（预编译二进制与编译器无关）
---

**编译结束**: 2026-08-05 17:07
**最终状态**: published
