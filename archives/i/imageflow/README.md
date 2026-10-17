# imageflow — 快速、安全的图像处理库与命令行工具

## 概述

imageflow 是一套高性能图像处理库与工具：

- `libimageflow.so` — 稳定的 C ABI（bindings/headers 提供 C/C++/Lua 头文件）
- `imageflow_tool` — 命令行工具（RIAPI querystring / JSON job / diagnose）

Rust 2024 编写（cargo workspace，11 个成员 crate），C 编解码组件
（mozjpeg / libpng / libwebp / lcms2 / zlib）由 crates 内嵌静态编译。

- **上游**: https://github.com/imazen/imageflow
- **许可证**: AGPL-3.0-or-later（上游为 AGPLv3 或商业双许可）
- **类型**: 库 + 命令行工具（commands.json: tool）

## 适配版本

| 版本 | 状态 | 构建期 tool_requires |
|------|------|----------------------|
| 2.3.1_rc01 | 已适配（built） | rust-toolchain/1.97.1, openssl/3.5.6.1.1, zlib-ng-compat/2.3.3 |

## 鸿蒙适配要点

1. Rust 工具链由制品仓 `rust-toolchain/1.97.1` 提供（宿主=目标
   `aarch64-unknown-linux-ohos`，rustup 无法识别 HarmonyOS 宿主）；
   构建命令 `cargo build --locked --release --workspace --target aarch64-unknown-linux-ohos`
2. `cargo`/`rustc`/`librustc_driver` 复制到私有 build 目录后
   `binary-sign-tool -selfSign 1` 签名（OHOS 拒绝 execve 未签名 ELF）
3. cargo 运行期需要 OpenSSL 3.5+（系统为 3.0.16，缺 `SSL_get0_group_name`）：
   将静态包 `openssl/3.5.6.1.1` 的 PIC 归档重链为私有
   `libssl.so`/`libcrypto.so`；`libz.so` 由 `zlib-ng-compat/2.3.3` 重链
4. cargo git 依赖（imazen libpng/lcms2 fork、rust-custom-derive；前两者带
   `vendor` 子模块）在 GitHub 不可达时经 `ghfast.top` 镜像回退（E017）
5. 源码 tarball 无 `.git`：按上游 Cross.toml 方式注入 tag 元数据环境变量
6. 产物 `imageflow_tool` 与 `libimageflow.so` 均签名；包内不含系统同名库（R26）

## 测试

- 上游 cargo 测试（OHOS aarch64 实跑）：**290 passed / 0 failed / 4 ignored**
  （单元 99 + 集成 190 + tool self-test 1；ignored 为 upload/sync 与 riapi 环境类）
- `test_package/`：11 项断言（鸿蒙特有 6 项 + 真实图像处理 5 项，
  PNG→JPEG mozjpeg / PNG→PNG libpng）+ C ABI 消费者（clang 链接
  `libimageflow.so` 调用 version/context_create/destroy）
