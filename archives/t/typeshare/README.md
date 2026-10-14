# typeshare

从 Rust 类型定义同步生成其他语言类型文件（Typescript / Swift / Kotlin /
Scala / Go / Python）的命令行工具。

- 上游仓库：<https://github.com/1Password/typeshare>
- 许可证：MIT OR Apache-2.0
- 适配状态：见 `manifest.yaml` 与各版本目录

## 交付物

| 版本 | 产物 | 状态 |
|------|------|------|
| 1.13.4 | `bin/typeshare`（HarmonyOS PC aarch64 ELF） | built |

## 构建方式

纯 Rust / Cargo workspace，使用制品仓基础设施包 `rust-toolchain/1.97.1`
（`tool_requires`）交叉编译到 `aarch64-unknown-linux-ohos`；无 C/C++ 目标依赖。
详见 `1.13.4/notes.md`。
