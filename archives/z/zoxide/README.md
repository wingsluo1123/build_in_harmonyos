# zoxide

zoxide 是一个更智能的 cd 命令。它会记录你访问最频繁的目录，让你只需几个按键就能"跳转"到目标目录。

- **主页**：https://github.com/ajeetdsouza/zoxide
- **许可证**：MIT
- **编程语言**：Rust

## 可用版本

| 版本 | 状态 | 构建方式 |
|------|------|----------|
| 0.9.8 | 已发布 (published) | 预编译 musl 二进制 + elfldr |

## OHOS 平台适配

zoxide 是 Rust 项目。在 OHOS 平台上，rustc 编译器会发生段错误（SIGSEGV），无法从源码编译。
本次构建使用 GitHub Release 预编译的 aarch64-unknown-linux-musl 静态二进制，通过 elfldr
（OHOS ELF 加载器）在 OHOS 上运行。

### 关键信息
- **二进制**：aarch64-unknown-linux-musl 静态 ELF，通过 elfldr 加载
- **加载器**：elfldr（TLS 段较小，无需 fd_loader）
- **Conan 配方**：下载预编译二进制，创建 elfldr 包装脚本
- **功能测试**：--version、add、query --list、query --score、init bash、remove 等全部通过
- **测试报告**：reports/test-report.md
