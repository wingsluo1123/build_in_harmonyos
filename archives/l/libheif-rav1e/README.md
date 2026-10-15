# libheif-rav1e

libheif 的 **rav1e（AV1）编码后端插件模块**。本包交付上游 libheif 1.23.0 树内的 CMake
目标 `heif-rav1e`（产物 `libheif-rav1e.so`），以及它运行所必需的宿主 `libheif.so`
（`ENABLE_PLUGIN_LOADING=ON`）。rav1e 编码器本体在包内树构建（官方 v0.7.1 源码，
经 OHOS Rust 工具链产出 `librav1e.a` + `rav1e.h`，静态链入插件）。

## 功能概述

- 在 libheif 中提供 **AV1 静图编码**能力（`heif_compression_AV1`），实现文件是上游树内的
  `libheif/plugins/encoder_rav1e.cc`（其特点是走 rav1e 的通用尺寸 C API，输入像素格式
  比 SVT-AV1/aom 后端更宽）；
- 插件以独立 `MODULE` 形态安装到 `<libdir>/libheif/`，由宿主在 `heif_init()` 时 `dlopen`
  并注册编码器（`heif_have_encoder_for_format(heif_compression_AV1) == 1`）；
- 同时交付宿主 `libheif.so`：仓库既有的 `libheif/1.22.2` 是 `ENABLE_PLUGIN_LOADING=OFF`
  的 codec-free 核心，运行期根本不装载插件，因此不能作为本包依赖。

## OHOS 适配

- **构建系统**：CMake（父 tarball）+ 包内树构建的 rav1e（cargo，Rust 1.97.1 OHOS 工具链）。
- **无源码补丁**（`patches: {}`）：上游 libheif 与 rav1e 源码均零修改，也不注入任何
  `__OHOS__` 平台宏（R8/PF5）。OHOS SDK libc++ 隐藏 C++20 ranges 算法的问题由配方内
  编译期宏 `_LIBCPP_ENABLE_EXPERIMENTAL` 解决。
- **Rust 工具链接入**：`tool_requires` `rust-toolchain/1.97.1`（签名私有 cargo/rustc 拷贝）
  + `cbindgen/0.28.0`（生成 `rav1e.h`）+ `openssl/3.5.6.1.1`（cargo 运行期 libssl/libcrypto
  relink）。crates.io 走 rsproxy.cn sparse 镜像。手法与仓库 upstream 分支权威配方
  `archives/r/rust-rav1e/0.7.1` 一致。
- **插件目录可移植性**：上游把默认插件目录编译期钉死（`heif_version.h` 的
  `LIBHEIF_PLUGIN_DIRECTORY` = 构建时的 `<prefix>/lib/libheif`，即 Conan 缓存里的绝对
  路径），跨缓存/跨机不可移植。本包用 `package_info()` 的 `runenv_info` 导出
  `LIBHEIF_PLUGIN_PATH`（上游 `libheif/plugins_unix.cc:37` 优先读该变量）解决。
- **无 `packaging/`**：按 ARCHIVE-SPEC v3.0，`packaging/` 已废弃，本包不创建。
- **无命令行工具**：只构建 `heif` 宿主 + `heif-rav1e` 插件模块，不安装任何可执行文件，
  故无 `commands.json`（R38）。

## 依赖关系

- **编译期**：无 Conan `requires`。rav1e 本体在包内树构建（官方 v0.7.1 源码）；
  `rust-toolchain/1.97.1`、`cbindgen/0.28.0`、`openssl/3.5.6.1.1` 为 `tool_requires`
  （构建工具，不进产物链接）。
- **运行期**：本包自带宿主 `libheif.so` 与插件 `libheif-rav1e.so`；rav1e 的 C API 已
  **静态链入**插件（`librav1e.a`），无额外的运行期共享库。消费者只需 `conan install`
  本包并用 `conanrun` 环境运行，`LIBHEIF_PLUGIN_PATH` 与 `LD_LIBRARY_PATH` 会由
  VirtualRunEnv 自动带上。
- 为什么没有把 rav1e 写成 Conan 依赖：制品仓没有任何 `rav1e`/`librav1e`/`rust-rav1e` 包
  （W0 实测，见版本级 notes.md「W0 依赖判定」），而 R36 是机械门禁
  （`finish` step[5/10] 与 CI L0i 对 `requires()` 逐条 `conan download --only-recipe`）。
  该形态在本仓库有已合并先例：`archives/l/libheif-svtenc/1.23.0`（内树构建 SVT-AV1）、
  `archives/l/libheif-aom/1.23.0`（内树构建 libaom）、`archives/h/handbrake/1.11.2`
  （contribs 全部内树构建、无 Conan 包依赖）。

## 测试

- **消费者功能测试**（`test_package/`，R34）：15/15——宿主 dlopen 插件、注册 AV1 编码器、
  真实编码一张 AVIF。
- **上游 rav1e `cargo test`**（`test_package` 阶段，R51）：**452/452 通过**。
- **上游 libheif CTest/Catch2 套件**：在独立的 testing-preset 测试构建里**真跑**，
  **N′ = 212 通过（PASS 212 / FAIL 0 / SKIP 0）**，NOT_RUN 5（逐项原因见版本级 notes.md 6.2）。
  测试所需的编解码后端（dav1d / libde265 / x265 / openjpeg / openjph / libtiff）以
  `tool_requires` 接入——只服务 build 阶段的上游测试构建，**不进入交付包的 `requires` 面**。

## 参考资料

- libheif 上游：<https://github.com/strukturag/libheif>
- rav1e 上游：<https://github.com/xiph/rav1e>
- 本仓库既有归档：`archives/l/libheif/1.22.2`（codec-free 核心）、
  `archives/l/libheif-svtenc/1.23.0`、`archives/l/libheif-aom/1.23.0`、
  `archives/l/libheif-dav1d/1.23.0`、`archives/r/rust-rav1e/0.7.1`（upstream 分支权威配方）
