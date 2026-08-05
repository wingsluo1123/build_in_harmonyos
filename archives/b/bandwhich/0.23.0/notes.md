# bandwhich 0.23.0 适配笔记

## 编译环境
- 构建系统: cargo (Rust)
- 编译日期: 2026-08-05
- 编译器: clang/clang++ (Rust 1.97.1 via Harmonybrew)
- 状态: built

## 编译步骤

1. 安装 Rust 工具链: `brew install rust` (Harmonybrew 提供 aarch64-unknown-linux-ohos target)
2. 安装 libpcap: `brew install libpcap` (pnet crate 依赖)
3. 创建 cc/c++ 符号链接指向 clang/clang++ (Rust linker 默认查找 cc)
4. 设置 PKG_CONFIG_PATH 包含 libpcap 的 pkgconfig 目录
5. 执行: `cargo build --release`
6. 安装: 复制 `target/release/bandwhich` 到 `$PREFIX/bin/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | linker `cc` not found | HarmonyOS 无 cc 符号链接 | 创建 cc→clang, c++→clang++ 符号链接 |
| 2 | pnet crate 找不到 libpcap | libpcap 未安装 | 通过 Harmonybrew 安装 libpcap |
| 3 | GitHub tag 前缀差异 | tag 名为 v0.23.0 非 0.23.0 | URL 使用 refs/tags/v0.23.0 |

## 源码修改

无补丁，源码未修改。

## 依赖版本

- Rust 1.97.1 (Harmonybrew)
- libpcap 1.10.6 (Harmonybrew / Conan 制品仓)
- clang 15.0.4 (系统自带)

## 验证结果

```bash
$ cargo build --release
    Finished `release` profile [optimized] target(s) in 2m 05s

$ cargo test --release
    14 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out

$ ./target/release/bandwhich --version
bandwhich 0.23.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/bandwhich | ~4.9MB | ELF shared object, aarch64 |

## 注意事项

- bandwhich 是 Rust CLI 工具，非 C/C++ 库
- pnet crate 依赖 libpcap C 库，需要通过 PKG_CONFIG_PATH 或 LIBPCAP_LIB_DIR 环境变量定位
- Rust target 为 aarch64-unknown-linux-ohos，target_os 匹配为 "linux"，procfs crate 正常包含
---

**编译结束**: 2026-08-05 06:48
**最终状态**: published
