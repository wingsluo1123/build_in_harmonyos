# hyperfine 1.20.0-r0 适配笔记

## 编译环境
- 构建系统: Rust (Cargo) — 但 rustc 在 musl 平台上 SIGSEGV，无法源码编译
- 编译日期: 2026-08-06 (Conan 适配)
- 编译器: N/A (使用预编译二进制)
- 状态: built

## Conan 适配方案

由于 rustc 在鸿蒙 musl 平台上崩溃 (SIGSEGV)，采用预编译二进制策略：

1. 源码: Alpine Linux edge/community aarch64 APK (`hyperfine-1.20.0-r0.apk`)
   - URL: https://dl-cdn.alpinelinux.org/alpine/edge/community/aarch64/hyperfine-1.20.0-r0.apk
   - SHA256: 511a1fcc8643c9f40237c20f972b2eb9375caf9d82a1cd17671c0d749410ba00
2. APK 解压 (tar.gz 格式)，提取 `usr/bin/hyperfine` 二进制
3. man 页面从 GitHub 源码 (`doc/hyperfine.1`) 提取，放入 `res/` 目录
4. 通过 Conan recipe (`conanfile.py`) 打包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | rustc SIGSEGV on musl | 鸿蒙 musl 平台不支持 Rust 编译器 | 使用 Alpine Linux 预编译 aarch64 musl 二进制 |
| 2 | GitHub releases 缺少 aarch64-musl variant | hyperfine CI 只编译 x86_64-musl 和 arm-musleabihf | 从 Alpine Linux APK 获取 aarch64 musl 二进制 |
| 3 | 补全文件无法生成 | 需要 Rust 编译 (clap_complete) 生成 | 跳过补全文件 (Rust 无法编译) |

## 依赖版本

- musl libc: /lib/ld-musl-aarch64.so.1 (系统内置)
- libgcc_s.so.1: ~/usr/local/lib/libgcc_s.so.1 (已预装)

## Conan 配方说明

- `package_type = "application"` (命令行工具，非库)
- `settings = "os", "arch"` (预编译二进制，不需要编译器设置)
- `source()`: 下载 Alpine APK 并解压
- `build()`: 无 (预编译二进制)
- `package()`: 复制二进制到 bin/，man 页面到 share/man/man1/
- `package_info()`: bindirs = ["bin"]

## 验证结果

```bash
$ hyperfine --version
hyperfine 1.20.0
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (预编译二进制打包) |
| conandata.yml | 源码 URL + SHA256 |
| test_package/ | 测试包 (--version, --help, benchmark) |
| res/hyperfine.1 | man 页面 |
| commands.json | 命令行工具声明 (软件级) |

## 注意事项

- 此二进制为 Alpine Linux 预编译，动态链接 musl libc
- 需系统提供 /lib/ld-musl-aarch64.so.1 和 libgcc_s.so.1
- 补全文件 (bash/zsh/fish) 需要 Rust 编译，当前无法生成
- 不可源码编译，未来版本升级需继续使用 Alpine 预编译方案
---

**编译结束**: 2026-08-06 20:46
**最终状态**: built
