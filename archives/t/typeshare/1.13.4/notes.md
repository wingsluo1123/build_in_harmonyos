# typeshare 1.13.4 适配笔记

## 编译环境

- 构建系统: Cargo（Rust workspace：`annotation` `core` `lib` `cli`，edition 2021）
- 目标: `aarch64-unknown-linux-ohos`（HarmonyOS PC arm64）
- Rust 工具链: `rust-toolchain/1.97.1`（制品仓基础设施包，`tool_requires`）
- 交叉链接器: OHOS SDK clang 15.0.4（`aarch64-unknown-linux-ohos-clang`）
- 编译日期: 2026-10-13
- 状态: built

## 编译步骤

1. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<同> --build='typeshare/*'` → EXIT=0（13:42:10 → 13:44:26）
2. 配方 `build()` 内部：
   - `_prepare_signed_toolchain()`：复制 `cargo`/`rustc` + `librustc_driver-*.so`，
     **以及 `lib/rustlib/<target>/lib/*.so`（含 `libstd-*.so`）**，用
     `binary-sign-tool -selfSign 1` 自签名后平铺进工具链 `lib/`
   - `_prepare_runtime_libs()`：Harmonybrew OHOS **openssl** bottle（cargo 运行期
     `libssl.so` / `libcrypto.so`；`libz.so` 由 OS 镜像满足，**不使用**第三方 zlib bottle
     —— 见「问题 #4」）
   - `_prepare_cxx_shared()`：SDK `libc++_shared.so` 复制 + 自签名
     （`librustc_driver` 动态依赖 OHOS C++ 运行库，加载器不搜 SDK arch 子目录）
   - `_prepare_test_runner()`：注入 `CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_RUNNER`，
     使测试进程先命**已签名**的 dylib（详见下「问题 #1」）
   - `_fetch_cargo_deps()`：`cargo fetch --locked`（110 包，rsproxy.cn 稀疏源）
   - `_run_upstream_tests()`：`cargo test --release --locked --target … --workspace --all-features --tests --no-fail-fast`
   - `_run_upstream_determinism_test()`：重放 `tests/justfile` 的 determinism 样例（100 输入 × 2 次运行 → 逐字节比对）
   - `_cargo_build()`：`cargo build --release --locked --target … -p typeshare-cli`（默认 features）
   - `_sign_binaries()`：`binary-sign-tool -selfSign 1` 签名 `typeshare`

## 关键问题与修复

| # | 问题（首个真实错误） | 根因 | 修复 |
|---|---------------------|------|------|
| 1 | `Runnning unittests src/lib.rs (target/release/deps/typeshare_annotation-…)` → `Error loading shared library libstd-6cb83eb787a5e858.so` + 大量 `symbol not found`，`exit status: 127`，cargo test rc=101 | proc-macro crate 的测试 harness 以 `prefer-dynamic` 链接，`DT_NEEDED libstd-<hash>.so`（无 RUNPATH）；cargo 启动测试进程时把 `<sysroot>/lib/rustlib/<target>/lib` **前置**到 `LD_LIBRARY_PATH`，而该目录来自只读工具链载荷、其中 `libstd-*.so` **未签名**；OHOS 拒绝加载未签名共享库，前置副本遮蔽了 `toolchain/lib/` 中的已签名副本 | ①`_prepare_signed_toolchain()` 复制 + 自签名 `rustlib/<target>/lib/*.so` 到工具链 `lib/`；②`_prepare_test_runner()` 用 target runner 把已签名目录前置到 `LD_LIBRARY_PATH`（runner 路径必须无空格） |
| 2 | `FileNotFoundError: [Errno 2] No such file or directory: 'sed'`（`_run_upstream_determinism_test`） | `tests/justfile` 依赖 `just`+`sd`，OHOS 镜像均无；`sed`/`diff` 也不在构建进程 PATH 上 | 用 Python 标准库完成等价操作：同一全局正则 `(struct )(\w+)` → `\1\2<i>` + 字节级比对 |
| 3 | test_package：`typeshare -l scala` rc=101 `panicked at core/src/language/scala.rs:131: package name must be provided`；`--generate-config -o <f>` rc=2 | 上游设计：Scala 生成器要求显式 package（缺省 panic）；clap `Output` 组内 `--output-file` 与 `--generate-config` 互斥且 `<DIRECTORIES>...` 为 required | 测试参数修正：`--scala-package com.typeshare.consumer`；`--generate-config -c <file> <src>` |
| 4 | **CI PR #15632 `conan-build-test` ❌**（23:47 首次失败）：`NotFoundException: Not found: https://harmonybrew.atomgit.com/bottles/zlib-ng-compat-2.3.3_2.arm64_ohos.bottle.tar.gz`（栈：`build()` 121 → `_rust_environment()` 158 → `_prepare_runtime_libs()` → `download()`） | 把**非必需**的第三方 CDN bottle 当作硬依赖：① `libz.so` 实测由 OS 镜像 `/usr/lib/libz.so.1` 满足（本机 `LD_LIBRARY_PATH` 不含任何外部 libz 时 `cargo --version` 仍正常，退出码 0）；② harmonybrew 的 revision 会轮换且 CDN 复制不均（同一 URL 本机 HTTP 200、CI worker 404；`2.3.3_1`/`2.3.3` 均已 404）。openssl bottle 在 CI 上同一轮下载成功，证明问题只出在这一条非必需依赖 | 从 `RUST_RUNTIME_BOTTLES` **移除 zlib 条目**（只保留必需的 openssl），并让取不到 bottle 时抛出带排查指引的明确报错（指明 URL/revision 轮换与 URL+sha256 需同步更新），不再以深层 NotFoundException 形式出现 |

**上游源码修改：0**（无补丁，全部修复属构建环境适配）。

## 依赖

| 依赖 | 版本 | 类型 | 证据 |
|------|------|------|------|
| rust-toolchain | 1.97.1 | 构建期 `tool_requires` | 基础设施包；`conan download rust-toolchain/1.97.1 -r=ohpcd` EXIT=0（含 OHOS armv8 binary，2026-09-09 上传） |
| openssl@3（harmonybrew OHOS bottle） | 3.6.5 | 构建期运行库（cargo 自身 DT_NEEDED libssl/libcrypto，**必需**） | `readelf -d cargo` → NEEDED libssl.so / libcrypto.so / libz.so；bottle HTTP 200，sha256 `f8c37456…327c` 实测；系统 `/usr/lib/libssl.so.3` 缺 `SSL_get0_group_name`，注册表 `openssl/3.5.8.1` 为 static-only（`shared: False`，无 .so），故无替代来源 |
| （已移除）zlib-ng-compat bottle | 2.3.3_2 | ~~构建期运行库（cargo DT_NEEDED libz.so）~~ | **已移除**：实测 libz 由 OS 镜像 `/usr/lib/libz.so.1` 满足（不提供外部 libz 时 cargo 仍可运行）；且该 CDN bottle 在 CI worker 上 404 —— 见「问题 #4」 |

其余 110 个 crate 全部由 cargo 依 `Cargo.lock` 从 crates.io（rsproxy.cn 镜像）自动拉取，
**无 C/C++ 目标依赖包**（`Cargo.lock` 内 `-sys` crate 仅 core-foundation-sys/macOS、
js-sys/wasm、windows-sys/Windows 平台门控与纯 Rust 的 linux-raw-sys；无 openssl-sys /
libgit2-sys / ring / libz-sys 等，亦无 git 依赖）。

> 注：harmonybrew bottle 版本会轮换且 CDN 复制不均——`openssl@3-3.6.4_1` / `3.6.4` / `3.6.3`
> 与 `zlib-ng-compat-2.3.3_1` / `2.3.3` 均已 404；本配方据此**只保留必需**的 openssl bottle
> （`3.6.5`，URL + sha256 双固化），并在取不到时抛出带排查指引的明确报错。

## 上游测试清点（R51 三步法）

### 清点

上游 CI（`.github/workflows/ci.yml`）共 5 个 job，其中 2 个是测试门：

| CI job | 命令 | 本平台可行性 |
|--------|------|--------------|
| Test | `cargo test --all-features`（ci.yml:41） | 可行（等价入口 `--workspace --all-features --tests`） |
| check-deterministic | `just --justfile tests/justfile determinism`（ci.yml:63） | 可行（Python 标准库等价重放） |
| Check / fmt / clippy | `cargo check` / `cargo fmt --check` / `cargo clippy` | 非测试用例；工具链无 rustfmt/clippy 组件，未纳入统计 |

静态 `#[test]` 清点：

| 位置 | 形式 | 用例数 |
|------|------|--------|
| `core/tests/agnostic_tests.rs` | 字面量 `#[test]` | 11 |
| `core/tests/snapshot_tests.rs` | `tests!` 宏展开（用例目录 × 目标语言） | 309 |
| `cli/src/config.rs` | 内联单元测试 | 8 |
| `core/src/**` | 内联单元测试 | 33 |
| `lib/src/**` | 内联单元测试 | 25 |
| `annotation/src/**` | 过程宏 crate，无 `#[test]` | 0 |
| `tests/justfile`（shell 驱动样例） | `just determinism` | 1 个样例（100 输入 × 2 次运行） |
| **合计** | | **386** |

### 执行

```bash
cargo test --release --locked --target aarch64-unknown-linux-ohos \
    --workspace --all-features --tests --no-fail-fast
```

日志（留档副本）：
- 构建内（第 5 轮 conan create）：`/storage/Users/currentUser/Desktop/lan work/.task-typeshare/logs/conan_create_5.log`
- 独立复跑（`run_upstream_verify.py`，rc=0）：`/storage/Users/currentUser/Desktop/lan work/.task-typeshare/logs/upstream_cargo_test.log`

### 结果（实测）

| 测试目标 | 用例 | 通过 | 失败 | 跳过 |
|----------|------|------|------|------|
| `typeshare` lib 单元测试（lib/src） | 25 | 25 | 0 | 0 |
| `typeshare-annotation` lib 单元测试（proc-macro） | 0 | 0 | 0 | 0 |
| `typeshare-cli` bin 单元测试（cli/src/config.rs） | 8 | 8 | 0 | 0 |
| `typeshare-core` lib 单元测试（core/src） | 33 | 33 | 0 | 0 |
| `tests/agnostic_tests.rs` 集成测试 | 11 | 11 | 0 | 0 |
| `tests/snapshot_tests.rs` 集成测试 | 309 | 309 | 0 | 0 |
| **合计** | **386** | **386** | **0** | **0** |

逐项用例名称（386 条）：`reports/upstream-test-cases.md`。

### 上游 shell 驱动样例

`tests/justfile` 的 `determinism`：100 份生成输入、两次运行产物必须一致。
实测通过——**100 输入 × 2 次运行，产物逐字节一致（32,722 B）**。

### doctest 说明

上游 `cargo test --all-features` 亦含 doctest；`rust-toolchain/1.97.1` 基础设施包不含
`rustdoc` 可执行文件（`bin/` 仅 cargo/rustc/cargo-clippy/clippy-driver/rust-analyzer/
rust-gdb/rustfmt 等；`rustdoc` 仅有 man 页），因此 doctest 在本平台**无对应可运行入口**，
未运行，如实申报，不视为漏测。

## 验证结果

```bash
$ bin/typeshare --version
typeshare 1.13.4

# 代码生成（消费者侧实测，见 reports/test-report.md）
$ bin/typeshare src -l typescript -o out.ts          # rc=0，177 B，export interface Sample
$ bin/typeshare src -l swift     -o out.swift        # rc=0，380 B，struct Sample
$ bin/typeshare src -l kotlin    -o out.kt           # rc=0，234 B，data class Sample
$ bin/typeshare src -l scala --scala-package com.x -o out.scala   # rc=0，490 B，case class Sample
$ bin/typeshare --generate-config -c typeshare.toml src           # rc=0，295 B，含 [scala] 等节
```

ELF: `e_machine=183`(AArch64) / `PT_INTERP=/lib/ld-musl-aarch64.so.1` / 含 `.codesign` 与
`.note.ohos.ident` / `DT_NEEDED` 仅 `libc.so`（静态 Rust std）/ PIE + GNU_RELRO。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/typeshare` | 8,570,752 B | HarmonyOS PC aarch64 ELF（含 OHOS 代码签名） |
| `licenses/LICENSE-APACHE` / `licenses/LICENSE-MIT` | — | 上游许可证 |
| `res/README.md` | — | 上游 README |

## 注意事项

- 本配方**未**修改上游任何源码/构建文件；无 `patches/`。
- 交付二进制保持 cargo **默认 features**（TypeScript/Swift/Kotlin/Scala），与
  `cargo install typeshare-cli` 及上游 cargo-dist 发布物一致；Go/Python 是上游文档标注的
  实验性 opt-in features，测试阶段以 `--all-features` 覆盖其生成器用例。
- Scala 语言后端要求显式 `--scala-package`（或配置文件 `[scala] package`），否则上游
  代码会 panic——这是上游行为，非平台缺陷。

## 环境侧说明（非本包问题；均已在框架修复分支 `feat/framework-fixes-ohc-20261013` 修复并回归）

本包适配过程中暴露的框架/检查器缺陷**不属于本包**，已单独在框架修复分支修复（不混入本 PR）：

| # | 现象 | 根因 | 修复 |
|---|------|------|------|
| 1 | 本地 W3 后 `conandata.yml` 残留 `[gh-proxy.com 镜像, 官方 URL]` 列表 + `.orig`，命中 PF7（R39） | `ci/conan/build_and_test.sh` 的镜像改写无还原；EXIT trap 只还原其后才建立的 `predl_cache` 备份 | 镜像改写前把官方源原文备份到 `.build-cache/predl_cache/conandata.yml.pristine` 并注册退出还原；预下载的还原函数优先使用该 pristine 备份；`.orig` 备份不再落在归档树内。E2E 实测：`finish` 后 conandata.yml 为**仅官方 URL**、无任何 `.orig`/`.ghfast-bak` 残留 |
| 2 | 未提交分支跑 W3 必被 JC 拦（命中其它任务已合入 main 的 8 个 `.staging-verified`/`.build-closed`） | `junk_check.sh` 的 `incremental` 模式在 `git diff origin/main...HEAD` 为空时回退 `git ls-files` **整仓**扫描 | 无提交分支改为按「工作区相对 origin/main 的实际变更」（staged+modified+untracked，.gitignore 自动排除）扫描（新 `worktree` 模式）；E2E 实测 W3 直接通过，**无需再临时改索引** |
| 3 | CLI 包 PR 无法通过 `create-pr`（PF9 判软件级 `commands.json` 为「缺版本目录层」） | `preflight.check_branch_and_paths()` 要求 archives 路径深度 ≥5，与 R38/PF8（`commands.json` 必放软件级）冲突；已合入的 `archives/r/rumdl` 同样可复现 | PF9 为软件级元数据（`commands.json`/`README.md`/`manifest.yaml`）加白名单；白名单外的浅层散落文件仍被拦（负例已验） |
| 4 | `finish` 的 `gen_summary` 崩溃 `'str' object has no attribute 'append'` | `summary.py::_parse_yaml_simple` 遇到同名键先标量后列表（`archives/q/qpdf/12.3.2/manifest.yaml` 形态）时对 str 调 append | 同名键标量→列表提升；14916 个 manifest 全量解析 0 失败 |
| 5 | `finish` step10 就绪预检要求 legacy `packaging/`（对 conanfile.py v3 配方不适用）；step5b 报 `E219/E253/E305` 必填字段为空 | ① step8 未复用「conanfile.py 优先」口径；② `workflow_checks` 的 kv 字段解析不支持 YAML 块标量（`root_cause: |` 后跟缩进正文被判空） | ① 有 `conanfile.py` 即视为就绪（与 `check_prerequisites` 一致）；② 新增 `_parse_kv_fields()` 解析块标量/续行，真空白仍判空（正负例已验） |
| 6 | 本机 Python `subprocess` 无法解析**任何**裸命令名（`ls/git/python3/tar/curl…` 全部 `FileNotFoundError`，绝对路径与 `shell=True` 正常），使框架外呼静默降级（`_run()` 把 rc 记成 1） | OHOS 平台差异：`execvp` 风格的 PATH 解析在本机不可用 | `utils.resolve_exec()`（复用既有 `find_executable`）统一解析为绝对路径，并应用于 `preflight`/`workflow_checks`/`gitcode_pr`/`submission`/`graph`/`requirements` 全部外呼点；实测 `_run(["git", …])` 由 rc=1 变为 rc=0 |

**仓库级既有问题（非本任务、未纳入本 PR）**：`archives/l/libXext` 与 `archives/l/libxext` 为大小写
变体，在大小写不敏感文件系统上互相覆盖，导致工作树恒显示该包 2 个文件 modified。

**`G0 clean-verify` 说明**：该步骤面向 autotools `./configure` 流程，对 Cargo 配方不适用
（报「找不到原始 tarball」）；SKILL 明示其为非阻塞步骤。
---

**编译结束**: 2026-10-13 23:37
**最终状态**: built
