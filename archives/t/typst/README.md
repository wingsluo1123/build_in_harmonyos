# Typst

Typst 是一个基于标记语言的现代排版系统，兼具 LaTeX 的强大排版能力与 Markdown 式的简洁语法。本仓适配产物为 typst 命令行工具（`typst`），可把 `.typ` 文档编译为 PDF / PNG / SVG，支持增量编译、字体发现、数学公式、参考文献等。

- **Homepage**: https://typst.app
- **Repository**: https://github.com/typst/typst
- **License**: Apache-2.0
- **Build System**: Cargo (Rust workspace, edition 2024, rust-version 1.92)
- **Type**: Command-line tool
- **Category**: doc (文档排版)

## 版本

| 版本 | 状态 | 构建日期 | 说明 |
|------|------|----------|------|
| 0.15.1 | built | 2026-10-12 | Rust 排版系统 CLI，交叉编译 aarch64-unknown-linux-ohos，OpenSSL 静态链接，产物含 OHOS code signature |

## 功能

- **编译文档**：`typst compile doc.typ out.pdf`（亦支持 PNG/SVG）
- **增量编译**：`typst watch`
- **表达式求值**：`typst eval '1+2*3'`
- **字体发现**：`typst fonts`（自动发现系统字体）
- **数学排版**：内建完整数学公式支持
- **多目标输出**：PDF / PNG / SVG

## 包结构

```
bin/typst        # ELF64 aarch64 OHOS musl 二进制（已签名，含 .codesign / .note.ohos.ident）
```

## OHOS 适配要点（详见 0.15.1/notes.md）

- 纯 Rust 工程，Cargo 交叉编译到 `aarch64-unknown-linux-ohos`
- Rust 工具链由制品仓基础设施包 `rust-toolchain/1.97.1` 以 `tool_requires` 提供
- 工具链二进制无 code signature → `binary-sign-tool -selfSign 1` 自签名后使用
- 唯一外部 C 依赖 **OpenSSL**（经 `typst-kit/system-downloader` 无条件启用），静态链接 conan `openssl/3.5.8.1`

## 依赖

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| openssl | 3.5.8.1 | 运行时·强制 | typst-kit/system-downloader → openssl-sys，静态链接 |
| rust-toolchain | 1.97.1 | 构建期 tool_requires | 基础设施包，Rust 编译器工具链 |

其余 ~425 个依赖均为 crates.io Rust crate，由 cargo 依 `Cargo.lock` 自动拉取。
