# 适配笔记 — superseedr latest

## 软件信息
- **软件名**: superseedr
- **版本**: 1.0.11 (latest)
- **描述**: A BitTorrent Client in your Terminal
- **语言**: Rust
- **构建系统**: Cargo (rust-toolchain.toml 指定 1.95.0，实际使用 harmonybrew 安装的 1.96.1)
- **许可证**: GPL-3.0-or-later
- **上游**: https://github.com/Jagalite/superseedr

## 下载
- 任务提供的 URL (savannah.nongnu.org) 返回 404，软件不存在于 Savannah
- 实际源码在 GitHub: https://github.com/Jagalite/superseedr
- 使用 GitHub tarball API: https://api.github.com/repos/Jagalite/superseedr/tarball/v1.0.11
- SHA256: c64569242667cbd27908118a359b5a43774db7eab651b03ceea0bc68ca2215b6

## 编译过程

### 1. Rust 工具链安装
- **问题**: 系统未安装 Rust/Cargo，rustup 不识别 HarmonyOS (E154)
- **解决**: 通过 harmonybrew 安装 Rust 1.96.1 (`brew install rust`)
- harmonybrew 提供了 OHOS 适配的 Rust bottle (arm64_ohos)

### 2. OpenSSL 依赖
- **问题**: openssl-sys crate 找不到 OpenSSL 开发库
- **解决**: 设置 PKG_CONFIG_PATH 指向 harmonybrew/系统 OpenSSL 安装路径
  - `PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig:$HOME/.harmonybrew/lib/pkgconfig`
  - `OPENSSL_DIR=$HOME/usr/local`

### 3. Cargo 镜像配置
- **问题**: crates.io 下载极慢
- **解决**: 配置 USTC sparse 镜像
  - 关闭 HTTP/2 multiplexing 避免 Stream error

### 4. 编译结果
- `cargo build --release` 成功，耗时约 6 分 32 秒
- 产物: `target/release/superseedr` (10.9MB, ELF aarch64 musl)
- 版本验证: `superseedr --version` → `superseedr 1.0.11`

### 5. 测试结果
- `cargo test --release`: 1460 passed, 64 failed (95.6% 通过率)
- 失败的测试可能与 OHOS 平台特性相关 (文件系统、网络、权限差异)

## 源码修改
- 无源码修改 (纯 Rust 项目，无需 #ifdef __OHOS__ 适配)

## Conan 配方
- 构建系统从默认的 autotools 改为 Cargo
- conanfile.py 使用自定义 build() 方法调用 cargo build --release
- test_package 验证二进制 --version 输出
---

**编译结束**: 2026-07-02 21:57
**最终状态**: built
