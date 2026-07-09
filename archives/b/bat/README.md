# bat

## 简介

bat 是一个 `cat(1)` 的增强替代工具，具有语法高亮和 Git 集成功能。它支持自动语法高亮（对多种编程和标记语言）、Git 集成（显示文件修改标记）、分页、文件拼接、主题定制等特性。由 sharkdp 开发（与 fd 同一作者），使用 Rust 编写。

## OHOS 适配

- bat 是 Rust 项目，OHOS 上 rustc 1.87.0 存在段错误 (SIGSEGV) 问题，无法从源码编译
- 使用 GitHub 官方发布的预编译 aarch64-unknown-linux-musl 静态二进制
- 通过 fd_loader 加载器在 OHOS 上运行 musl 静态二进制
- **关键发现**: bat 的 `--version` 可以用 elfldr 运行，但文件读取和 stdin 处理会段错误
- **根因**: elfldr 不设置辅助向量中的 AT_PHENT，导致 musl TLS 初始化不完整
- **解决方案**: 使用 fd_loader（自定义 ELF 加载器，包含 AT_PHENT=56 修复），所有功能正常
- fd_loader 与 fd 工具共用同一个加载器（fd_loader.c 源码在 patches/ 目录中）
- 无需任何源码修改或补丁

## 依赖

无外部编译依赖（使用预编译 musl 静态二进制 + fd_loader 加载器，自包含运行）。

## 功能验证

```bash
# 版本确认
bat-wrapper --version
# 输出: bat 0.26.1 (979ba22)

# 基本文本显示
echo "Hello World" | bat-wrapper
# 输出: Hello World

# Python 语法高亮
echo "print('hello')" > test.py && bat-wrapper test.py

# JSON 高亮
echo '{"key":"value"}' > test.json && bat-wrapper test.json

# 显示非打印字符
bat-wrapper --show-all test.py

# 行号显示
printf "line1\nline2\nline3\n" | bat-wrapper --number
# 输出:
#    1 line1
#    2 line2
#    3 line3
```

## 参考

- 官网: https://github.com/sharkdp/bat
- 源码: https://github.com/sharkdp/bat/archive/refs/tags/v0.26.1.tar.gz
- 预编译二进制: https://github.com/sharkdp/bat/releases/download/v0.26.1/bat-v0.26.1-aarch64-unknown-linux-musl.tar.gz
