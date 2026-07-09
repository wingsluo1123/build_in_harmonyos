# just 1.43.1 适配笔记

## 编译环境
- 构建系统: custom (Rust/Cargo — 源码编译不可行)
- 编译日期: 2026-07-01
- 编译器: clang/clang++ (用于 elfldr)
- 状态: published (conan-verify 全门禁通过)

## 编译策略

just 是 Rust 项目，使用 Cargo 构建系统。在 OHOS 上 rustc 1.87.0 段错误 (SIGSEGV)，
无法从源码编译。采用预编译 musl 二进制 + elfldr 加载器方案。

### 策略1: 源码编译 (失败)
```bash
cargo build --release
# rustc -vV → signal: 11, SIGSEGV
```

### 策略2: 预编译 musl 二进制 + elfldr (成功)
```bash
# 下载 aarch64-unknown-linux-musl 静态二进制
curl -kL https://ghfast.top/https://github.com/casey/just/releases/download/1.43.1/just-1.43.1-aarch64-unknown-linux-musl.tar.gz
tar xzf just-musl.tar.gz
# 通过 elfldr 加载运行
elfldr just --version → just 1.43.1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | OHOS 缺少 CA 证书 | curl -k 跳过验证; ohc-run.py 已有 SSL fallback |
| 2 | HMDFS 硬链接失败 | HarmonyOS 文件系统不支持硬链接 | 修改 init_build.py copytree 添加 symlinks=True |
| 3 | rustc 段错误 | rustc 1.87.0 在 OHOS 上 SIGSEGV | 使用预编译 musl 二进制替代源码编译 |
| 4 | GitHub 下载超时 | 中国大陆网络访问 GitHub 不稳定 | 使用 ghfast.top 镜像 (E017) |
| 5 | Conan 2.x API 变更 | deps_cpp_info 已移除 | 改用 self.dependencies["just"].package_folder |
| 6 | /tmp 只读 | HarmonyOS /tmp 不可写 | 使用 $HOME/tmp 替代 |

## 验证结果

```bash
$ elfldr ~/usr/local/bin/just --version
Entry: 0x422938 SP: 0x5ada886610 argc=2 aligned=1
just 1.43.1

$ ~/usr/local/bin/just-wrapper --version
just 1.43.1
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| just | 4.1MB | 静态 musl ELF64 AArch64 二进制 |
| just-wrapper | 50B | elfldr 包装脚本 |

## 注意事项

- rustc 在 OHOS 上不可用，所有 Rust 项目需使用预编译二进制方案
- elfldr 是运行 musl 静态二进制的关键工具
- conanfile.py 使用 ghfast.top 镜像 URL 以避免下载超时
- just 是单文件命令行工具，不需要库文件
---

**编译结束**: 2026-07-03 15:09
**最终状态**: published
