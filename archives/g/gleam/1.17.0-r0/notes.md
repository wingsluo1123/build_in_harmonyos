# gleam 1.17.0-r0 适配笔记

## 编译环境
- 构建系统: Rust (Cargo) — 从源码编译
- 编译日期: 2026-08-06
- 编译器: Rust 1.97.1 (Harmonybrew), clang 15.0.4 (系统)
- 状态: built

## 编译步骤

### 1. 环境准备
1. 安装 Rust 工具链 (via Harmonybrew)
   - `brew install rust` → rustc 1.97.1, cargo 1.97.1
   - Rust target: aarch64-unknown-linux-ohos
2. 配置 clang 编译器 (系统自带)
   - CC=/data/service/hnp/bin/clang
   - CXX=/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang++
   - AR=/data/service/hnp/bin/ar
3. 配置 crates.io 镜像 (rsproxy.cn)
   - 在 ~/.cargo/config.toml 中配置 rsproxy-sparse 镜像

### 2. 源码获取
- 从 GitHub 下载 v1.17.0 源码
- URL: https://github.com/gleam-lang/gleam/archive/refs/tags/v1.17.0.tar.gz
- SHA256: 644db4b25596d5f27f03614ef1cc10646baaabbd559407acc278bb24c6502f8b

### 3. 源码补丁
- **fix-rustls-ring.patch**: 将 reqwest 的 TLS 后端从 aws-lc-rs 切换为 ring
  - 原因: aws-lc-sys 的汇编符号在 OHOS 上链接失败 (undefined bn_* symbols in bcm.c)
  - 修改: compiler-cli/Cargo.toml 中 `features = ["rustls"]` → `features = ["rustls-no-provider"]`
  - 添加: rustls + ring 作为直接依赖
  - 添加: gleam-bin/src/main.rs 中安装 ring crypto provider

### 4. 编译
```bash
cargo build --release --bin gleam
```
- 编译时间: ~3分钟
- 产物: target/release/gleam (27.4MB)
- 链接类型: 动态链接 musl libc (/lib/ld-musl-aarch64.so.1)
- 依赖: 仅 libc.so (系统提供)

### 5. 签名与验证
1. binary-sign-tool sign -selfSign 1 -inFile gleam -outFile gleam-signed
2. ./gleam-signed --version → "gleam 1.17.0" ✓

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 预编译静态 musl 二进制 SIGSEGV | Rust static musl binary 与 HarmonyOS 不兼容 (E081) | 从源码编译，生成动态链接 musl 二进制 |
| 2 | aws-lc-sys 链接失败 | aws-lc-sys 汇编符号未编译 (OHOS 平台未识别) | 切换到 ring crypto provider |
| 3 | crates.io 不可访问 | 网络限制 | 使用 rsproxy.cn 镜像 |
| 4 | cargo 找不到 cc linker | clang 不在 PATH 中 | 设置 CC=/data/service/hnp/bin/clang |
| 5 | 删除 Cargo.lock 导致版本不兼容 | cargo 解析到不兼容的新版本 | 保留原始 Cargo.lock |

## 知识提取

### Rust 项目在 HarmonyOS 上的编译
- Rust 1.97.1 (Harmonybrew) 可以正常工作，之前的 rustc SIGSEGV 问题已解决
- 默认 target 为 aarch64-unknown-linux-ohos，生成动态链接 musl 二进制
- 需要配置 crates.io 镜像 (rsproxy.cn) 才能下载依赖
- aws-lc-rs 的汇编代码在 OHOS 上无法正确编译/链接，需用 ring 替代

### 预编译二进制 vs 源码编译
- GitHub 官方 aarch64-unknown-linux-musl 二进制是**静态**链接，在 OHOS 上 SIGSEGV
- Alpine APK 中的二进制是**动态**链接 musl，可以在 OHOS 上运行
- 从源码编译生成的二进制也是**动态**链接 musl，可以正常运行
- 结论: 动态链接 musl 二进制是 OHOS 上运行 Rust 项目的正确方式
---

**编译结束**: 2026-08-06 14:36
**最终状态**: built
