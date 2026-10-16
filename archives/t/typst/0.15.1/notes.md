# typst 0.15.1 适配笔记

## 编译环境

- 构建系统: Cargo（Rust workspace，edition 2024，rust-version 1.92）
- 目标: `aarch64-unknown-linux-ohos`（HarmonyOS PC arm64）
- Rust 工具链: `rust-toolchain/1.97.1`（制品仓基础设施包，`tool_requires`）
- 交叉编译器: OHOS SDK clang 15.0.4（`aarch64-unknown-linux-ohos-clang`）
- 编译日期: 2026-10-12
- 状态: built

## 编译步骤

1. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<same> --build=typst/*`
2. 配方 `build()` 内部：
   - `_prepare_signed_toolchain()`：复制 `cargo`/`rustc` + `librustc_driver` + `libstd` 并 `binary-sign-tool -selfSign 1` 自签名
   - `_prepare_runtime_libs()`：Harmonybrew OHOS openssl bottle（cargo 运行期 libssl/libcrypto）
   - `_fetch_cargo_deps()`：`cargo fetch --locked`（rsproxy.cn 镜像 + git 依赖经 GitHub 镜像）
   - `_run_upstream_tests()`：上游测试（`cargo test --workspace --tests`）
   - `_cargo_build()`：`cargo build --release --target aarch64-unknown-linux-ohos -p typst-cli`
   - `_sign_binaries()`：`binary-sign-tool -selfSign 1` 签名 `typst`

## 关键问题与修复

| # | 问题（首个真实错误） | 根因 | 修复 |
|---|---------------------|------|------|
| 1 | `conan create` 报 zlib bottle 404 | below 配方沿用的 `zlib-ng-compat-2.3.3_1` bottle URL 已失效；实测 cargo 1.97.1 仅 DT_NEEDED libssl/libcrypto（无 libz） | 从 `RUST_RUNTIME_BOTTLES` 删除 zlib，仅保留 openssl3 |
| 2 | `typst-macros --lib` 报 `Error loading shared library libstd-6cb83eb787a5e858.so` | proc-macro 测试二进制 DT_NEEDED `libstd-*.so`；OHOS 拒绝加载**未签名**共享库 | `_prepare_signed_toolchain()` 额外复制 + 自签名 `lib/rustlib/<target>/lib/*.so` 到 toolchain `lib/`（进 LD_LIBRARY_PATH） |
| 3 | `cargo test --workspace` 的 doctest 全部 `rustdoc: No such file or directory` | `rust-toolchain/1.97.1` 基础设施包**不含 rustdoc 二进制**（`bin/` 仅 cargo/rustc/rustfmt/clippy 等，rustdoc 仅 `share/man/man1/rustdoc.1`） | 测试命令改用 `--tests`（单元 + 集成），排除 doctest；见下方「上游测试清点」说明 |
| 4 | 集成测试报告生成 panic（`tests/src/report/mod.rs:75` `git blame` unwrap） | 源码来自 tarball，无 `.git`；harness 生成 HTML 报告时对 `tests/ref/*/hashes.txt` 做 `git blame` | 仅在有失败时触发；本平台 4 项字体测试差异触发该 panic（见下），属报告展示环节，不改变测试结论 |

## 上游测试清点（R51 三步法）

### 清点

上游测试位于 `tests/` 集成测试 crate（`typst-tests`）与各 crate 的 `#[test]` 单元测试：

- 集成测试：`tests/suite/**/*.typ`（222 个 `.typ` 文件，逐 `--- name ---` 段展开为用例），
  入口 `tests/src/tests.rs`（`[[test]] name="tests" harness=false`）
- 单元测试：各 `crates/*/src`、`crates/typst-cli/tests/smoke.rs`
- 上游 CI 命令：`.github/workflows/ci.yml:58-59` `cargo test --workspace --no-run` / `cargo test --workspace --no-fail-fast`

### 执行

```bash
cargo test --release --target aarch64-unknown-linux-ohos --workspace --tests --no-fail-fast
```

日志：`.plan` 外存于构建目录 `cargo_test.log`；本任务留档
`/storage/Users/currentUser/Desktop/lan work/.task-typst/logs/upstream_cargo_test.log`

### 结果（实测）

| 目标 | 用例 | 通过 | 失败 | 跳过 |
|------|------|------|------|------|
| typst-cli `tests/smoke.rs` | 17 | 17 | 0 | 0 |
| typst-eval (lib) | 2 | 2 | 0 | 0 |
| typst-html (lib) | 2 | 2 | 0 | 0 |
| typst-ide (lib) | 76 | 76 | 0 | 0 |
| typst-kit (lib) | 5 | 5 | 0 | 0 |
| typst-layout (lib) | 7 | 7 | 0 | 0 |
| typst-library (lib) | 34 | 34 | 0 | 0 |
| typst-pdf (lib) | 2 | 2 | 0 | 0 |
| typst-syntax (lib) | 40 | 40 | 0 | 0 |
| typst-utils (lib) | 17 | 17 | 0 | 0 |
| typst-macros (lib) | 0 | 0 | 0 | 0 |
| 其余 lib/bin（typst/bundle/docs/fuzz/realize/render/svg/timing/wrapper） | 0 | 0 | 0 | 0 |
| **typst-tests 集成套件** | **3684** | **3680** | **4** | **0** |
| **合计** | **3886** | **3882** | **4** | **0** |

### 4 项平台差异失败（确定性，非偶发）

| 用例 | 源 | 失败输出 |
|------|----|---------|
| `block-clip-svg-glyphs` | tests/suite/layout/container.typ:239 | svg, pdf |
| `shaping-emoji-bad-zwj` | tests/suite/layout/inline/shaping.typ:65 | svg, pdf |
| `shaping-font-fallback` | tests/suite/layout/inline/shaping.typ:32 | svg, pdf |
| `text-font-properties` | tests/suite/text/font.typ:4 | svg, pdf |

- 均涉及**彩色 emoji（Noto Color Emoji CBDT/COLR）/ 可变字体 / RTL 复杂整形**的渲染字节。
- **确定性**：同一二进制连跑两次 new 哈希完全一致；
  **与优化档无关**：release 与 debug 两档 new 哈希逐字节相同
  （release: `5ae3a11a…`/`d7d27195…`/`ea87032a…`/`02d9f71e…` 等；
   debug 同值）→ 判定为 **aarch64-unknown-linux-ohos 平台确定性渲染差异**，
  非编译错误、非测试逻辑缺陷。
- 参考为哈希制比对（`tests/ref/*/hashes.txt`），无参考图片可 diff（参考图片经 git 历史获取，tarball 源码无 `.git`）。

### doctest 说明

上游 `cargo test --workspace` 包含 doctest；本平台**无法执行 doctest**：
`rust-toolchain/1.97.1` 基础设施包不含 `rustdoc` 可执行文件。故测试命令采用
`--tests`（单元 + 集成，覆盖全部 `#[test]` 与 `.typ` 套件），doctest 未运行，
如实申报，不视为漏测（无对应可运行入口）。

## 依赖

| 依赖 | 版本 | 类型 | 证据 |
|------|------|------|------|
| openssl | 3.5.8.1 | 运行时·强制（静态链接） | `crates/typst-cli/Cargo.toml:58-71` typst-kit `system-downloader` 无条件启用 `dep:openssl`（`crates/typst-kit/Cargo.toml:79`）；`conan download openssl/3.5.8.1 -r=ohpcd --only-recipe` EXIT=0 |
| rust-toolchain | 1.97.1 | 构建期 `tool_requires` | 基础设施包；`conan download rust-toolchain/1.97.1 -r=ohpcd` EXIT=0 |

其余 ~425 个依赖均为 crates.io Rust crate，由 cargo 依 `Cargo.lock` 自动拉取。

## 验证结果

```bash
$ typst --version
typst 0.15.1 (unknown commit)

$ typst compile hello.typ hello.pdf     # EXIT=0 → 16616 B PDF
$ typst compile --format png hello.typ hello.png   # EXIT=0 → PNG
$ typst eval "1+2*3"                     # → 7
$ typst fonts                            # → 238 字体族（含系统字体）
```

ELF: `e_machine=183`(AArch64) / `PT_INTERP=/lib/ld-musl-aarch64.so.1` / 含 `.codesign` 与 `.note.ohos.ident`。

## 已知限制

- 集成测试 4 项（彩色 emoji / 可变字体 / RTL）输出哈希与上游参考不一致（见上），
  属平台确定性渲染差异，已在 R51 申报表列明。
- doctest 无法运行（工具链缺 rustdoc）。
---

**编译结束**: 2026-10-12 17:54
**最终状态**: built
