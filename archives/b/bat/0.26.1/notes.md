# bat 0.26.1 适配笔记

## 编译环境
- 构建系统: custom（Rust/cargo，使用预编译 musl 二进制）
- 编译日期: 2026-07-02
- 编译器: clang/clang++（用于 fd_loader 兼容性）
- 状态: published

## 编译步骤

1. **init-build**: 下载源码包 v0.26.1.tar.gz 并初始化归档目录
2. **cargo build（失败）**: rustc 1.87.0 在 OHOS 上段错误 (SIGSEGV)，无法从源码编译
3. **下载预编译二进制**: 从 GitHub releases 下载 `bat-v0.26.1-aarch64-unknown-linux-musl.tar.gz`
4. **elfldr 测试（部分失败）**: `elfldr bat --version` 成功，但文件读取和 stdin 处理段错误
5. **fd_loader 测试（全部通过）**: 使用 fd_loader（含 AT_PHENT 修复），6 项功能测试全部通过
6. **conan-init**: 生成 conanfile.py（预编译二进制 + fd_loader wrapper 方案）
7. **conan-verify**: G1-G4 + L2/L4/L5 全部通过
8. **finish**: 归档关闭，状态标记为 published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | 鸿蒙 Python 缺少 CA 证书 | 安装 Mozilla CA 证书到 `/storage/Users/currentUser/usr/local/ssl/cert.pem` |
| 2 | rustc 1.87.0 段错误 | OHOS 平台已知限制 | 使用 GitHub 预编译 aarch64-musl 静态二进制 |
| 3 | elfldr 文件读取段错误 | elfldr 不设置 AT_PHENT，musl TLS 初始化不完整 | 改用 fd_loader（含 AT_PHENT=56 修复），所有功能正常 |
| 4 | /tmp 只读 | 鸿蒙 E002 平台限制 | 测试文件使用 `$HOME/tmp` 替代 |

### 关键发现：elfldr vs fd_loader

| 加载器 | --version | --help | 文件读取 | stdin 管道 | --show-all | --number |
|--------|-----------|--------|---------|-----------|------------|----------|
| elfldr | ✅ | ✅ | ❌ SIGSEGV | ❌ SIGSEGV | ❌ SIGSEGV | ❌ SIGSEGV |
| fd_loader | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**根因**: elfldr 不在辅助向量中设置 AT_PHENT 条目。`--version` 和 `--help` 只打印静态文本，不触发 TLS 依赖路径；但文件 I/O 和语法高亮等复杂操作需要完整的 TLS 支持，因此段错误。fd_loader 设置 AT_PHENT=sizeof(Elf64_Phdr)=56，修复了此问题。

## 源码修改

无源码修改（使用预编译二进制方案）。fd_loader.c 源码从 fd 项目复制到 patches/ 目录。

## 依赖版本

- Python 3.12.8
- Conan 2.30.0（OHOS 适配版）
- clang 15.0.4
- fd_loader（自定义 ELF 加载器，含 AT_PHENT 修复）
- rustc 1.87.0（不可用，段错误）

## 验证结果

```bash
# 版本确认
$ bat-wrapper --version
bat 0.26.1 (979ba22)

# stdin 文本显示
$ echo "Hello World" | bat-wrapper
Hello World

# Python 文件读取
$ bat-wrapper test.py
print('hello')
def greet(name):
    print(f"Hello, {name}!")
greet("World")

# --show-all 非打印字符
$ bat-wrapper --show-all test.py
print('hello')␊
def·greet(name):␊

# --number 行号显示
$ printf "line1\nline2\nline3\n" | bat-wrapper --number
   1 line1
   2 line2
   3 line3
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/bat-0.26.1-ohos-aarch64.tar.gz | 6,065,588 字节 | 发布 tar.gz（含 bin/bat + bin/fd_loader + bin/bat-wrapper） |
| conanfile.py | 3,167 字节 | Conan 配方（预编译二进制 + fd_loader wrapper） |
| conandata.yml | 603 字节 | 源码 + 二进制 SHA256 校验和 |
| test_package/ | - | Conan 测试包（bat-wrapper --version smoke test） |
| patches/fd_loader.c | 4,949 字节 | fd_loader 加载器源码（从 fd 项目复制） |

## 注意事项

- bat 与 fd 同为 sharkdp 开发，两者都需要 fd_loader（不能使用 elfldr）
- **重要教训**: bat 的 --version 能用 elfldr 运行曾导致误判不需要 fd_loader，实际文件 I/O 功能仍需 fd_loader
- 后续 sharkdp 系列工具应默认使用 fd_loader，不做 elfldr 尝试
- 二进制为 musl 静态链接，无运行时库依赖
- G0 干净构建验证会失败（Rust 项目无 configure 脚本），这是预期行为
- conan-verify（G2）是真正的验证，已全部通过

---

**编译结束**: 2026-07-02 01:10
**最终状态**: published
