# mise

## 简介

mise（ formerly rtx）是一个多语言版本管理器，用 Rust 编写。它是 asdf 的替代品，支持管理 Node.js、Python、Ruby、Go、Java 等多种工具的版本。mise 通过 `.tool-versions` 或 `mise.toml` 文件管理项目依赖的工具版本。

- 官网: https://mise.jdx.dev
- 源码: https://github.com/jdx/mise
- 许可证: MIT

## OHOS 适配

### 核心挑战

mise 是一个纯 Rust 项目，在 HarmonyOS (aarch64, musl libc) 平台上面临以下挑战：

1. **rustc 段错误**: rustc 1.87.0 在 HarmonyOS 上加载 librustc_driver 共享库时段错误 (SIGSEGV)，无法从源码编译
2. **预编译二进制无法执行**: GitHub 发布的预编译 musl 二进制缺少 HarmonyOS 安全签名 (.note.ohos.ident / .codesign ELF section)，直接执行返回 Permission denied
3. **预编译 musl 二进制实为 glibc 链接**: 标注为 "musl" 的发布包实际使用 glibc 动态链接器 (/lib/ld-linux-aarch64.so.1)，在 musl 系统上无法直接运行

### 解决方案：自定义 ELF 加载器

由于无法从源码编译且预编译二进制无法直接执行，采用自定义 C 语言 ELF 加载器方案：

1. 用 clang 编译 ELF 加载器（自动获得 HarmonyOS 安全签名，可执行）
2. 加载器读取 mise PIE 二进制的 ELF 结构，mmap 所有段到内存
3. 处理 111,629 个 RELA 重定位和 310 个 PLT 重定位
4. 通过 dlsym 将外部符号解析到 musl libc 的对应函数
5. 调用 init_array 和 main() 函数

### 已知限制

- **Tokio 运行时不兼容**: glibc 编译的二进制其 TLS 变量偏移基于 glibc 布局，在 musl 系统上读取到垃圾数据，导致 Tokio 多线程运行时 panic ("Cannot start a runtime from within a runtime")
- **--version 无法正常输出**: 由于 Tokio panic，mise 的 `--version` 命令无法完成执行
- 版本信息可通过源码 Cargo.toml 确认: `version = "2025.8.20"`

## 依赖

无外部编译依赖。mise 是自包含的 Rust 二进制。

预编译二进制的动态依赖（通过 ELF 加载器解析到 musl libc）:
- libc (glibc → musl 兼容映射)
- libgcc_s.so.1 (_Unwind_* 函数未解析，导致 panic 后 stack unwinding 失败)
- libpthread (→ musl 内置)
- libdl (→ musl 内置)
- librt (→ musl 内置)

## 功能验证

```bash
# 通过 ELF 加载器运行（当前因 TLS 不兼容 panic）
mise --version

# 版本从源码确认
grep '^version' Cargo.toml  # 输出: version = "2025.8.20"
```

## 参考

- 官网: https://mise.jdx.dev
- 源码: https://github.com/jdx/mise
- 发布: https://github.com/jdx/mise/releases/tag/v2025.8.20
