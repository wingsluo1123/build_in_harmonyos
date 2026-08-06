# git-xet 0.2.1 适配笔记

## 编译环境
- 构建系统: Rust (预编译二进制, 无法从源码编译)
- 编译日期: 2026-08-06
- 编译器: N/A (使用 GitHub 预编译二进制)
- 状态: built

## 背景

git-xet 是 XetHub/HuggingFace 的 Git 扩展, 用于大文件存储. 源码为 Rust,
使用 `edition = "2024"`, 需要 Rust 1.85+ 编译器. HarmonyOS 上 rustc
在 musl 上运行时 SIGSEGV 崩溃, 无法从源码编译.

## 适配方案

使用 GitHub releases 预编译二进制 (git-xet-linux-aarch64.zip) +
Alpine gcompat 兼容层适配 musl HarmonyOS:

### 1. 预编译二进制
- 下载: https://github.com/huggingface/xet-core/releases/download/git-xet-v0.2.1/git-xet-linux-aarch64.zip
- 原始格式: glibc-dynamic ELF (依赖 libc.so.6/libm.so.6/ld-linux-aarch64.so.1)

### 2. patchelf 适配
```bash
patchelf --replace-needed libc.so.6 libgcompat.so.0 git-xet
patchelf --replace-needed libm.so.6 libgcompat.so.0 git-xet
patchelf --replace-needed ld-linux-aarch64.so.1 libglibc-shim.so git-xet
patchelf --set-interpreter /lib/ld-musl-aarch64.so.1 git-xet
patchelf --set-rpath "$ORIGIN/../lib" git-xet
```

### 3. glibc-shim 库 (自定义)
从 glibc-shim.c 编译 libglibc-shim.so, 提供 glibc 特有但 musl 缺失的符号:
- pthread_mutexattr_setrobust (robust mutex)
- pthread_mutex_consistent (robust mutex)
- __res_init (resolver init)
- __res_state (resolver state)
- gnu_get_libc_version (version string)

### 4. Alpine 兼容库
| 库 | Alpine 包 | 说明 |
|----|----------|------|
| libgcompat.so.0 | gcompat-1.1.0-r4 | glibc 兼容层 (libc/libm 等函数) |
| libucontext.so.1 | libucontext-1.3.2-r0 | ucontext 实现 (gcompat 依赖) |
| libobstack.so.1 | musl-obstack-1.2.3-r2 | obstack 实现 (gcompat 依赖) |
| libgcc_s.so.1 | libgcc-14.2.0-r4 | GCC 运行时库 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 预编译为 glibc-dynamic | 依赖 libc.so.6 等, HarmonyOS 使用 musl | patchelf 替换 NEEDED + gcompat |
| 2 | /lib/ 只读, 无法放置 ld-linux-aarch64.so.1 | 内核只接受系统路径的 interpreter | patchelf --set-interpreter 替换 |
| 3 | glibc 特定符号缺失 | musl 不提供 robust mutex 等 | 编写 libglibc-shim.so stub |
| 4 | gcompat 依赖 libucontext/libobstack | Alpine 包间依赖 | 下载并打包全部依赖 |
| 5 | rustc SIGSEGV 崩溃 | Rust 在 musl 上运行不稳定 | 无法从源码编译, 使用预编译二进制 |

## 交付物

| 文件 | 说明 |
|------|------|
| bin/git-xet | 预编译+patchelf适配二进制 |
| lib/libglibc-shim.so | 自定义 glibc 符号 stub |
| lib/libgcompat.so.0 | Alpine glibc compat layer |
| lib/libucontext.so.1 | Alpine ucontext |
| lib/libobstack.so.1 | Alpine musl-obstack |
| lib/libgcc_s.so.1 | Alpine GCC runtime |
