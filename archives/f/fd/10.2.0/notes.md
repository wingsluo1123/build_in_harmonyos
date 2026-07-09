# fd 10.2.0 适配笔记

## 编译环境
- 构建系统: custom (Rust pre-built binary)
- 编译日期: 2026-07-02
- 编译器: clang/clang++ (for fd_loader), rustc 1.87.0 (unusable - SIGSEGV)
- 状态: published

## 编译步骤

1. **init-build**: 下载源码包 fd-v10.2.0.tar.gz (release tag)
2. **策略1 (失败)**: `cargo build --release` — rustc 1.87.0 段错误，无法编译 Rust 代码
3. **策略2 (失败)**: 下载预编译 musl 二进制 fd-v10.2.0-aarch64-unknown-linux-musl.tar.gz，通过 elfldr 运行 → SIGSEGV
4. **策略3 (成功)**: 编写 fd_loader.c 自定义 ELF 加载器，添加 AT_PHENT 修复，fd 成功运行

### 关键编译命令

```bash
# 下载预编译二进制
curl -kL https://ghfast.top/https://github.com/sharkdp/fd/releases/download/v10.2.0/fd-v10.2.0-aarch64-unknown-linux-musl.tar.gz -o ~/tmp/fd-musl.tar.gz
tar xzf ~/tmp/fd-musl.tar.gz -C ~/tmp/

# 编译自定义加载器
clang -o ~/tmp/fd_loader ~/tmp/fd_loader.c -O2

# 运行 fd
~/tmp/fd_loader ~/tmp/fd --version
# 输出: fd 10.2.0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | rustc SIGSEGV | OHOS 上 rustc 1.87.0 段错误 | 使用预编译 musl 二进制 |
| 2 | elfldr 运行 fd 段错误 | elfldr 未设置 AT_PHENT 辅助向量 | 编写 fd_loader.c 添加 AT_PHENT=56 |
| 3 | musl TLS 初始化崩溃 | 无 AT_PHENT 导致程序头循环无法前进，PT_TLS 未被发现 | fd_loader 正确设置 AT_PHENT 使 musl 能遍历程序头表 |

## 源码修改

无源码修改。fd_loader.c 是新增的自定义 ELF 加载器，不修改 fd 二进制本身。

## 依赖版本

- clang (OHOS 内置): 用于编译 fd_loader.c
- musl libc (fd 二进制内嵌): aarch64-unknown-linux-musl 静态链接

## 验证结果

```bash
$ ~/tmp/fd_loader ~/tmp/fd --version
[loader] starting
fd 10.2.0
[parent] exit 0
Exit code: 0

$ ~/tmp/fd_loader ~/tmp/fd --help
A program to find entries in your filesystem
Usage: fd [OPTIONS] [pattern] [path]...
Exit code: 0

$ ~/tmp/fd_loader ~/tmp/fd -e md . ~/tmp
(成功搜索到 .md 文件)
Exit code: 0

$ conan create (conan-verify G2)
RUN: "fd-wrapper" --version
[loader] starting
fd 10.2.0
[parent] exit 0
(PASS)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| fd | 3271096 bytes | 预编译 aarch64 musl 静态二进制 |
| fd_loader | 22912 bytes | 自定义 ELF 加载器 (含 AT_PHENT 修复) |
| fd-wrapper | 88 bytes | Shell 包装脚本 |

## 注意事项

- fd 必须通过 fd_loader 运行，不能直接执行或通过 elfldr 运行
- fd_loader 的 AT_PHENT 修复对其他有大型 TLS 段的 musl 静态二进制也适用
- 对比: just (TLS 32 bytes) 可通过 elfldr 运行，fd (TLS 2712 bytes) 需要 fd_loader

### 对话 #1: 编译策略探索

用户要求编译 fd 10.2.0 到 OHOS 平台。尝试了三种策略：
1. cargo build → rustc SIGSEGV 失败
2. elfldr + 预编译 musl → SIGSEGV 失败
3. fd_loader + 预编译 musl → 成功

通过断点追踪精确定位崩溃在 musl 的 `__set_tp` (msr tpidr_el0, x0)，根因是
elfldr 未设置 AT_PHENT 辅助向量条目，导致程序头循环无法正确遍历。

### 对话 #2: 归档文件补充

用户指出归档目录缺少 README.md 和 release tar.gz。补充创建软件级 README.md、
packaging/ 下的 release/debug tar.gz，并更新 notes.md 和 test-report.md。
---

**编译结束**: 2026-07-03 15:06
**最终状态**: published
