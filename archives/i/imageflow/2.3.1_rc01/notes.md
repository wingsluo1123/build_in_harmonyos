# imageflow 2.3.1_rc01 适配笔记

## 软件信息
- 上游仓库: https://github.com/imazen/imageflow
- 源码: tag `v2.3.1-rc01`（commit `0635e3863f950fa58c227eaec1d4b957e0f42fdc`，2026-03-31）
- 语言: Rust 2024（cargo workspace 11 个成员 crate + C 组件）+ C（bindings/headers、c_components/lib）
- 构建系统: cargo（产物 `libimageflow.so` C ABI cdylib + `imageflow_tool` CLI）
- 编译环境: HarmonyOS PC（aarch64, OHOS 6.0 profile），rustc/cargo 1.97.1（宿主=目标 `aarch64-unknown-linux-ohos`），clang 15（OHOS SDK 26.0.0.18）
- 编译日期: 2026-10-06

## 上游测试用例申报（R51 三步法）

### 1. 上游测试清点（静态统计）

全树 `#[test]` 宏共 **312** 个（`grep -rE '#\[test\]' --include='*.rs'`，平台同口径静态清点）；
workspace 成员口径为 **309** 个（排除 `c_components/tests` 3 例——上游 `Cargo.toml` members 中已注释排除）。

主要分布：

| 范围 | #[test] 数 |
|------|-----------|
| imageflow_core/tests/integration/visuals/* | 118 |
| imageflow_core/tests/integration/*（非 visuals） | 75 |
| imageflow_core/src/*（内嵌单元测试） | 63 |
| imageflow_core/tests/schema.rs + tests/skip/* | 1 + 5 |
| imageflow_types/src | 10 |
| imageflow_helpers/src | 10 |
| imageflow_abi/src | 9 |
| imageflow_riapi/src | 14 |
| imageflow_tool（src 1 + tests/test_tool.rs 1） | 2 |
| imageflow/src、append_only_set/src | 1 + 1 |
| c_components/tests | 3 |
| **合计** | **312** |

### 2. 上游测试实际运行（本机 = HarmonyOS PC aarch64，release profile）

| 命令 | 结果 |
|------|------|
| `cargo test --workspace --lib --bins` | **99 passed / 0 failed / 1 ignored** |
| `cargo test -p imageflow_core -- --skip visuals::` | **71 passed + 1 schema passed / 0 failed / 3 ignored** |
| `cargo test -p imageflow_core -- visuals::` | **118 passed / 0 failed** |
| `cargo test -p imageflow_tool_lib`（含 `tests/test_tool.rs` 自测） | **1 passed / 0 failed** |

**汇总：上游全树静态清点 312 例；OHOS aarch64 实跑 294 例 —— 290 passed / 0 failed / 4 ignored（有效通过率 100%）；未纳入本运行矩阵 18 例（含 `tests/skip/` 5、`c_components/tests` 3 及目标/条件编译差异项）。**

- ignored=4：`imageflow_riapi` 单元 1 例 + `sync::{backfill_diff_stats, sync_and_verify_uploads, verify_upload_log}` 3 例
  （sync 组需要 `REGRESS_UPLOAD_PREFIX`/`UPLOAD_REFERENCES` 上传环境，属设计内忽略）。
- doc-tests 无法运行：`rust-toolchain/1.97.1` 包内不含 `rustdoc`（工具链裁剪），属环境限制，非用例缺陷。

### 3. 失败用例逐项技术原因

无失败用例（0 failed）。

## 编译过程与平台适配

构建（配方内复现，clean conan create 通过）：

```bash
# 1) tool_requires: rust-toolchain/1.97.1 + openssl/3.5.6.1.1 + zlib-ng-compat/2.3.3
# 2) build_folder 内签名 rust 工具链（binary-sign-tool -selfSign 1）
# 3) 重链私有 cargo 运行库（libssl.so/libcrypto.so/libz.so）
# 4) cargo fetch（github 不可达时 ghfast.top 镜像回退）
# 5) cargo build --locked --release --workspace --target aarch64-unknown-linux-ohos
# 6) 签名产物 imageflow_tool + libimageflow.so
```

### 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `imageflow_types/build.rs` panic：`Failed to acquire GIT_COMMIT / GIT_DESCRIBE_ALWAYS_LONG` | 源码 tarball 无 `.git`；build.rs 要求 git 元数据（上游 CI 用 Cross.toml 给容器传同样变量） | 配方显式传入 5 个 env：`GIT_COMMIT=0635e3863f…`、`GIT_COMMIT_SHORT`、`GIT_DESCRIBE_ALWAYS=v2.3.1-rc01`、`GIT_DESCRIBE_ALWAYS_LONG=v2.3.1-rc01-0-g0635e3863f`、`GIT_OPTIONAL_TAG` |
| 2 | cargo/rustc 启动 EACCES（Permission denied） | rust-lang dist 二进制无 OHOS 代码签名，HarmonyOS 拒绝 execve 未签名 ELF | 复制 `cargo`/`rustc`/`librustc_driver-*.so` 到 `build_folder/rust-toolchain/`，`binary-sign-tool sign -selfSign 1` 自签名（幂等 marker；below/0.11.0 先例） |
| 3 | cargo 报 `SSL_get0_group_name: symbol not found` | cargo 1.97 动态依赖 OpenSSL 3.5+，系统 `/usr/lib/libssl.so.3` 为 3.0.16；Harmonybrew bottle 实测 404（外部资源失效） | 使用制品仓 `openssl/3.5.6.1.1`（静态 PIC，R26），构建期用 OHOS clang `-shared --whole-archive` 重链为私有 `libssl.so`/`libcrypto.so`（cbindgen/0.28.0 先例）；`libz.so` 由 `zlib-ng-compat/2.3.3` 同样重链、系统 zlib 兜底 |
| 4 | `cargo fetch` 卡死/失败（github.com 连接超时、Empty reply） | 大陆网络对 GitHub 不稳定（E017） | `GITHUB_MIRROR=https://ghfast.top/https://github.com/`，通过 `GIT_CONFIG_COUNT/KEY_0/VALUE_0` 设置 git `url.<mirror>.insteadOf`；`net.git-fetch-with-cli=true` 使 cargo 调用 git CLI——主仓库与 vendor 子模块均走镜像（实测 `From https://ghfast.top/...`）。探测 github 不可达才切镜像，可达则直连 |
| 5 | 两个 `-sys` fork 依赖带 `vendor` 子模块（libpng/lcms2 源码） | 上游用 git submodule 携带 C 源码；cargo 对 git 依赖会执行子模块拉取 | 镜像重写对子模块同样生效（`rust-libpng-sys`→`glennrp/libpng`、`rust-lcms2-sys`→`mm2/Little-CMS`）；checkout 后 `vendor/png.c`、`vendor/src/cmsalpha.c` 实证存在 |
| 6 | 产物 `DT_NEEDED: libz.so` | `flate2`/`lodepng` 动态引用系统 zlib（上游行为） | OHOS loader 默认搜索路径可解析（`/usr/lib/libz.so.1` 经 ld 缓存），`env -i` 实机验证可执行；包内不分发系统同名 `.so`（R26 / G3 通过） |

### 源码修改

无。`patches_applied: []` —— 所有平台适配收敛于 conanfile.py 的环境构造；
构建期由上游 build.rs 生成的文件（`bindings/headers/imageflow_*` 变体、
`imageflow_core/generated_idct.c` 等）不属于源码补丁。

## 依赖版本

| 依赖 | 版本 | 角色 |
|------|------|------|
| rust-toolchain | 1.97.1 | tool_requires（宿主=目标 aarch64-unknown-linux-ohos） |
| openssl | 3.5.6.1.1 | tool_requires（cargo 运行库重链源，静态包） |
| zlib-ng-compat | 2.3.3 | tool_requires（cargo 运行库重链源，静态包） |
| mozjpeg / libpng / libwebp / lcms2 / zlib（C 组件） | 由 cargo crates 内嵌静态编译 | 系统同名库静态（R26） |

## 验证结果

```bash
# conan-verify（8 门禁 G0-G4 + L2/L4/L5）：PASS
# conan create 干净构建：成功（reports/conan-create.log）
# test_package：11/11 断言通过（6 项鸿蒙特有 B1-B6 + 5 项真实图像处理 A1-A5）
#   [ok] B1 imageflow_tool AArch64 ELF / B2 PT_INTERP=ld-musl-aarch64.so.1 /
#        B3 含 OHOS code signature / B4 libimageflow.so AArch64 /
#        B5 .so 含 OHOS code signature / B6 无危险 RPATH/RUNPATH
#   [ok] A2 PNG->JPEG 8x8（mozjpeg）/ A4 PNG->PNG w=16（libpng）
# C ABI 消费者（clang 链接 libimageflow.so）：PASS
#   imageflow C ABI version 3.2 / abi_compatible(3,2)=true /
#   context_create OK / context_destroy OK
```

上游测试：全树静态清点 312 例；OHOS 实跑 290 passed / 0 failed / 4 ignored（见 R51 一节）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/imageflow_tool | ~5.2 MB | CLI（v1/querystring、v1/build、diagnose、examples） |
| lib/libimageflow.so | ~5.7 MB | 稳定 C ABI（imageflow ABI 3.2） |
| include/{imageflow_default,imageflow_lua,imageflow_pinvoke,imageflow_short}.h | - | C 头文件 |
| licenses/LICENSE | - | AGPL-3.0（上游双许可） |

## 注意事项

- 构建机/CI 需可访问 `rsproxy.cn`（crates 索引与下载）以及 GitHub 或 `ghfast.top`（cargo git 依赖，含子模块）。
- 首次 `cargo fetch` 约 900 MB（CARGO_HOME=$HOME/.cargo 复用缓存）。
- `libz.so` 运行期由 OHOS 系统提供（默认搜索路径），包内不分发（R26）。
- `rust-toolchain/1.97.1` 不含 `rustdoc`，上游 doc-tests 不可运行（环境限制）。
- 版本号 `2.3.1_rc01` 对应上游 `v2.3.1-rc01`；后续适配修复按 R37 递增后缀。
---

**编译结束**: 2026-10-12 18:51
**最终状态**: built
