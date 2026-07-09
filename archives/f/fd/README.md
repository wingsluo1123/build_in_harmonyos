# fd

一个简单、快速且用户友好的 `find` 替代工具。

fd 是一个用于在文件系统中查找条目的程序。它是基于 Rust 的现代 `find` 命令替代品，
具有合理的默认设置和彩色输出。

## 版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 10.2.0 | published | 2026-07-02 | 预编译 musl 二进制 + fd_loader（AT_PHENT 修复） |

## 编译方法

fd 是 Rust 项目。在 OpenHarmony (OHOS) 上，rustc 1.87.0 段错误 (SIGSEGV)，
无法从源码编译。因此使用 GitHub Release 的预编译 aarch64-unknown-linux-musl 二进制。

### 关键问题：elfldr 缺少 AT_PHENT

标准 `elfldr` ELF 加载器未设置 `AT_PHENT` 辅助向量条目。这会导致 musl 的 TLS
初始化对于具有大型 TLS 段的二进制文件（如 fd，.tdata 段 2712 字节）失败。
为此编写了自定义的 `fd_loader`，包含 `AT_PHENT` 修复。

### 为什么 just 能用 elfldr 而 fd 不能

- just 的 TLS 段很小（32 字节 .tdata，360 字节总计）
- fd 的 TLS 段很大（2712 字节 .tdata，3032 字节总计）
- 大型 TLS 段需要正确发现 PT_TLS 程序头，这依赖于 AT_PHENT

## 使用方法

```bash
# 通过 fd-wrapper（推荐）
fd-wrapper --version
fd-wrapper . /path/to/search
fd-wrapper "pattern" /path/to/search --max-depth 2

# 通过 fd_loader 直接调用
fd_loader /path/to/fd --version
fd_loader /path/to/fd . /path/to/search
```

## 链接

- **主页**：https://github.com/sharkdp/fd
- **许可证**：MIT
