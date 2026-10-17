# wpmeta 0.2.0 适配笔记（HarmonyOS PC / aarch64-unknown-linux-ohos）

- 上游：https://github.com/AOSC-Dev/wpmeta （AOSC-Dev，壁纸元数据生成器）
- 版本：0.2.0（tag `wpmeta-v0.2.0`，与 Arch Linux extra/wpmeta 0.2.0-2 同源）
- 源码：`https://github.com/AOSC-Dev/wpmeta/archive/refs/tags/wpmeta-v0.2.0.tar.gz`
  sha256 `a7b736ce218ddadeb19271cee6ce336a69daf686b7282103605456baef35fe38`（23 文件/30 tar 条目）
- 语言（R47）：`rust`（manifest `Cargo.toml`，11 个 `.rs` 主体源文件，占比 100%；
  虚拟 workspace = `localized` + `wpmeta` 两个成员，203 个 crates.io 锁定依赖）
- 构建系统：`cargo`（根 `Cargo.toml` 为虚拟 workspace manifest，`resolver = "3"`，
  `edition = "2024"`，rust-toolchain.toml 声明 stable channel）
- 目标：`aarch64-unknown-linux-ohos`（OHOS aarch64 / armv8，clang 15 仅为链接器，libc++，Release）
- 状态：built（conan create rc=0；上游 10/10 单测通过；test_package 10/10 通过；尚未上传制品仓）

## 编译步骤

```bash
# 1) 源码与 sha256 核验（官方源）
sha256sum wpmeta-0.2.0.tar.gz   # a7b736ce…fe38

# 2) 配方构建（Rust 工具链来自制品仓基础设施包 rust-toolchain/1.97.1）
conan create archives/w/wpmeta/0.2.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → cargo build --release --locked --target aarch64-unknown-linux-ohos（9m29s，203 crate）
# → cargo test  --release --locked --target aarch64-unknown-linux-ohos --lib --bins --tests（10/10）
```

真实命令、原始输出、退出码与日志路径：见本地 `reports/adaptation-report.md`（每一步含日志文件与 rc）。

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 解决方案（最小修改） |
|---|----------------------|------|----------------------|
| 1 | `NotFoundException: Not found: https://harmonybrew.atomgit.com/bottles/openssl%403-3.6.4.arm64_ohos.bottle.tar.gz`（conan get() 下载 cargo 运行期 bottle） | Harmonybrew bottle 仓轮换：weggli（2026-10-01）使用的 openssl@3 3.6.4 与 zlib-ng-compat 2.3.3_1 bottle 已下架（HTTP 404），同样命中 alacritty/libsignal-core 等先前配方引用的 3.6.4_1 / 2.3.3_2（不带 .1 后缀）也全部 404 | 从官方 formula API（`https://harmonybrew.atomgit.com/api/formula.jws.json`）取当前发布 bottle：openssl@3 3.6.5_1 `.bottle.1.tar.gz`（sha256 `ae1d5bf9…54ef2`）与 zlib-ng-compat 2.3.3_2 `.bottle.1.tar.gz`（sha256 `7092bfe7…4c51`），本地下载实测核验 sha256 后写入 conandata.yml |
| 2 | `PermissionError: [Errno 13] Permission denied` — `os.symlink` 在 `/storage/…/.conan2/p/b/…/rust-toolchain/lib/` 内创建链接失败 | HMDFS 文件系统不支持/拒绝 symlink（E077 家族）；weggli 当时同代码成功，本次目标路径策略变化 | `_link` 增加 OSError 回退：symlink 失败时按 rumdl 0.2.39 先例复制（目录 `copytree`、文件 `copy2`）；rust-toolchain 载荷 lib/ 实测 93 个文件均非符号链接，复制安全 |
| 3 | `cargo probe failed: [Errno 13] Permission denied: …/rust-toolchain/bin/cargo` | Conan 包内 `bin/cargo` 复制后仍无 `.codesign` 签名段，OHOS 加载器拒绝执行（EACCES） | `binary-sign-tool sign -selfSign 1` 对 cargo/rustc/librustc_driver 自签名，签名后 `cargo 1.97.1 (c980f4866 2026-06-30)` 探测通过（below/0.11.0 先例，配方内置） |
| 4 | test_package C5 断言失败：期望 stderr `No such file or directory`，实际为 `Error: Starting path … is not a directory`（walk.rs:81） | wpmeta 的目录遍历入口对源目录先做显式目录校验并抛出自定义 eyre 错误，不透传底层 io::Error | 断言改为 `is not a directory`（rc=1 不变），与上游实际行为一致 |
| 5 | CI `checkout-pr` 失败：`error: missing binary patch data for 'archives/w/wpmeta/0.2.0/test_package/fixtures/ohos_wallpaper.png'` + `binary patch does not apply to '…ohos_wallpaper_dark.png'`（随后 `patch: Unknown option 'fuzz=3'`，脚本报"PR 与 main 分支存在冲突"） | E650：CI 不 checkout PR 分支，而是 clone main 后 `curl <PR>.diff \| git apply`；GitCode 的 PR diff 端点对**新增二进制文件**只给出占位标记、不附二进制数据段，故 apply 必然失败（与 main 是否真实冲突无关，重试无效） | 按 E650 rec_priority 1（test-time 生成器，dbview PR #9495 / libsoil PR #12488 先例）落地：`git rm` 两枚 PNG，新增纯文本 `fixtures/make_wallpaper.py`（struct+zlib 程序化生成 64x64 PNG，恒定滤波字节与压缩等级 → 产物逐字节确定），由 test.sh 在运行期生成到 mktemp 私有目录；两变体互异，C4 的 `cmp` 映射断言保持有效 |

## 源码修改

无补丁：Cargo.lock 锁定的 203 个依赖（libc 0.2.178、getrandom 0.2.16/0.3.4、
rayon 1.11.0 等）均已包含 `aarch64-unknown-linux-ohos` 支持，构建输入逐字节
等于上游 tarball（E358 的锁图迁移在本包不需要）。

## 依赖版本

- rust-toolchain/1.97.1（tool_requires，制品仓 ohpcd 已发布，W0 conan download 验证）
- cargo 运行期（构建工具自身动态链接，不进入产物）：openssl@3 3.6.5_1、
  zlib-ng-compat 2.3.3_2（Harmonybrew OHOS bottle，sha256 固定）
- crates.io 依赖：上游 Cargo.lock 锁定的 203 个（含 rav1e 0.8.1/image 0.25.9/
  quantette 0.5.1/material-color-utilities 1.0.0-dev.18），全部经 rsproxy.cn
  稀疏镜像解析，`--locked` 保证锁图一致

## 验证结果

```bash
# 上游测试（build() 内真实执行，计数取自 cargo 框架输出）
cargo test --release --locked --target aarch64-unknown-linux-ohos --lib --bins --tests -- --test-threads=1
# localized: 3 passed（test_access / test_get_locale / test_serde）
# wpmeta:    7 passed（input 2 + gnome 2 + kde 1 + generate/mod 2）
HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "discovered": 10, "executed": 10,
  "passed": 10, "failed": 0, "skipped": 0, "expected_discovered": 10}

# test_package（消费者 + 鸿蒙特有，conan test 复跑验证）
HMBS_TEST_PACKAGE_RESULT={"status":"passed","framework":"bash","command":"test.sh",
  "discovered":10,"executed":10,"passed":10,"failed":0,"skipped":0}
# C1 version / C2 usage / C3 缺参报错 / C4 端到端+输出断言 / C5 坏源目录
# H1 AArch64 ELF / H2 musl interpreter / H3 预览 JPEG 生成+产物断言

# 构建产物
target/aarch64-unknown-linux-ohos/release/wpmeta → package bin/wpmeta（LLVM DWARF，
arm64-ohos 目标，/lib/ld-musl-aarch64.so.1 解释器）
```

## 与知识库的交互（W5）

- 命中：`E509`（cargo 运行期 OpenSSL 共享库 → bottle 注入路径直接沿用）；
  `E077`（未签名 ELF EACCES → binary-sign-tool 自签名沿用）；
  `E046`（HMDFS chmod 语义 → 工具链复制到私有目录后 chmod + 签名）；
  `E650`（PR 新增二进制测试图片 → CI checkout-pr 的 `git apply` 报
  `missing binary patch data`，重试必然复现；解法=测试期确定性生成器）。
  E650 的"一行判据"在本包 CI 日志上逐字命中：
  `error: missing binary patch data for '…/fixtures/ohos_wallpaper.png'`，
  且 diff 中新增二进制只有占位标记、无任何二进制数据段（新增文件全为文本）。
- 未命中（已登记草稿 E549-draft）：Harmonybrew bottle URL 轮换——bottle 仓会
  持续下架旧版 bottle，配方里的 bottle URL 会随时间腐烂；修复路径是从
  formula.jws.json（API）动态取当前 bottle URL + sha256 而非静态照抄先例配方
- 本次按 E650 沉淀的经验：测试用二进制输入一律走"纯文本生成器 + 测试期生成"，
  并在 MANIFEST.yml 中显式记录该约束与生成器契约（先例 dbview #9495、
  libsoil #12488、dbskkd-cdb .cdb 夹具）

## 任务对话记录

### 对话 #1 — 任务下发（2026-10-13）

- 用户下发目标库适配任务：`wpmeta 0.2.0`，要求读取适配 skill 后完整走通流程。
- W0 依赖检查：`rust-toolchain/1.97.1` 已在制品仓发布（conan download --only-recipe
  实证，R35 口径）；wpmeta 为纯 Cargo workspace，无其它 conan 级依赖。
- R47 语言预检：detected=rust 与任务语言一致；仓库 Rust 路径受支持
  （below/weggli/rumdl/alacritty 等 40+ 先例），按 rust 分支继续。
- 关键决策：① 零源码补丁（构建输入=上游 tarball）；② 上游 10 个 #[test] 在
  build() 内真实执行并持久化计数，test_package 复发证据；③ 鸿蒙特有用例 3 项
  （H1 AArch64 ELF / H2 musl interpreter / H3 预览 JPEG 产物）。

### 对话 #2 — CI 检出失败修复（2026-10-14）

- 现象：PR #15637 连续 3 次 CI 失败（#89898 / #90768 / #90985），均停在
  `checkout-pr`（`git-clone ✅ → checkout-pr ❌`，耗时 4.9s，L0/L1/test_package
  全未执行）；平台评论区诊断为"源码下载超时"，但完整日志显示 diff 已下载成功，
  真正报错是 `error: missing binary patch data for '…/ohos_wallpaper.png'`。
- 定位：命中知识条目 `E650`（判据：diff 对新增二进制只给占位行、git apply
  报 missing binary patch data）。根因是新增二进制文件不在 PR diff 中
  携带数据段 → `git apply` / `--3way` / `patch -p1` 相继失败，与 main 是否
  真实冲突无关（本 PR 14 个文件全为新增，merge-base 干净）。
- 修复（E650 rec_priority 1）：`git rm` 两枚 PNG 夹具，新增纯文本
  `test_package/fixtures/make_wallpaper.py`（标准库 struct+zlib 程序化生成
  64x64 PNG；每扫描线 filter=0、zlib level=9 → 产物逐字节确定，双跑校验一致），
  test.sh 运行期生成到 mktemp 私有目录；两变体像素互异 → C4 的 `cmp` 字节级
  映射断言保持判别力。MANIFEST.yml 新增 `fixtures_generated_at_test_time` 段
  记录该约束与生成器契约。
- 本地复验：`conan test` 10/10 通过（生成的 normal/dark 分别为 11667 / 9905
  字节，`bytes_equal_fixture=True`），上游 10/10 复发证据不变；新 PR diff 中
  新 diff 中已无任何二进制条目与占用行（13 个文件全为文本）。
---

**编译结束**: 2026-10-13 18:07
**最终状态**: built
