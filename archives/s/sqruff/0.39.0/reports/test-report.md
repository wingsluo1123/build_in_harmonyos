# sqruff 0.39.0 测试报告

> **项目**: sqruff v0.39.0（高性能 SQL linter/formatter，单一 CLI 二进制，内嵌 LSP）
> **测试日期**: 2026-10-12（2026-10-16 工具链与测试架构修订）
> **测试环境**: HarmonyOS HongMeng Kernel 1.12.0 aarch64（真机；Clang 15.0.4 / 制品仓 rust-toolchain 1.97.1）
> **测试类型**: 官方测试套件（cargo test workspace，build() 内执行）+ test_package 消费者测试

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游 libtest 用例 | 159 | 100% |
| 通过 (PASS) | 159 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 上游自带 ignore | 4 | — |
| 平台跳过（jinja/pyo3，上游官方开关） | 68 | — |
| 鸿蒙特有消费者用例 | 6 | 100% |

**核心功能通过率**: ✅ **100%**（159/159 libtest；12 个 harness=false 集成套件 rc=0；6/6 消费者用例）

- 上游官方套件：`SQRUFF_SKIP_UNSUPPORTED_TEMPLATERS=1 cargo test --locked -j 4
  --no-fail-fast --workspace --exclude sqruff-cli-python --exclude sqruff-wasm --tests`
  （真机框架 "test result:" 行对账：159 passed / 0 failed / 4 ignored / 0 filtered）
- 鸿蒙特有消费者用例：6/6（test_package/test.sh，真机运行打包产物）

---

## 二、测试结论

### 2.1 总体评价

✅ **通过** — 上游测试套件在 HarmonyOS aarch64 真机通过；打包产物 `bin/sqruff`
消费者用例全部通过；产物 `readelf` 实测 NEEDED 仅 `libc.so`（PIE + GNU_RELRO +
NX stack），无运行时第三方依赖。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| jinja 模板器用例依赖 pyo3/Python 绑定（上游经 maturin 安装），OHOS CLI 运行时不提供 | 68 个 fixture 用例 | 🟢 已解决（上游官方开关 `SQRUFF_SKIP_UNSUPPORTED_TEMPLATERS=1` 逐条跳过并如实申报） |
| doc-tests 阶段不可执行（工具链无 rustdoc） | 0 个可执行用例（静态核对 5 对文档块均为 ```ignore/```sql） | 🟢 平台先例，明确记录 |
| conan-verify G2 首轮因 ghfast.top 镜像超时下载失败 | 0（适配问题，非代码缺陷） | 🟢 已解决（改用官方 codeload 入口，sha256 逐字节一致） |
| test_package 就地运行时上游源码解压落位污染仓库工作树 | 1（工具链/流程问题） | 🟢 已解决（scratch 落位改 TMPDIR，CI JC5 门禁通过） |
| 平台 CI：harmonybrew bottle 固定 URL 404（仅保留每公式最新版），worker 无本机 cargo 时自举必挂 | 全部 CI 轮次（#93066/#93172 17-19s 即败） | 🟢 已解决（工具链改 ohpcd 制品仓 `rust-toolchain/1.97.1` tool_requires + `openssl/3.5.6.1.1` 重链私有 DSO，零外链；真机小验证与 conan-verify 均通过） |

### 2.3 可用功能清单

```
✅ sqruff lint      : 文件/目录/标准输入 SQL lint（human/json/github 输出，dialect/config 支持）
✅ sqruff fix       : 自动修复可修复违规（返回码语义：全修复=0，部分修复=1）
✅ sqruff format/parse/rules/templaters/info : 格式化/解析/规则/模板器查询
✅ sqruff lsp       : 内嵌 LSP 服务器（stdio 传输，initialize 握手已验证）
✅ 上游 159 个测试  : 规则矩阵（rules fixture 套件）/CLI UI 快照/fix 语义/config/dialect/
                       lineage/sqlinference/LSP 单元测试全通过
```

### 2.4 已知限制

1. jinja 模板器在 OHOS CLI 运行时不可用（上游将其实现为 pyo3/Python 绑定；上游
   x86_64 发布物同样不含 Python 绑定）——对应 68 个 fixture 用例按上游官方开关跳过，
   数量与原因已在 MANIFEST.yml/notes.md/PR 正文申报。
2. doc-tests 阶段因工具链无 rustdoc 未执行；静态核对 0 个可执行 doctest 受影响
   （详见 MANIFEST.yml）。
3. 上游自带 4 个 ignore（lineage Oracle/TODO 标记 3 个 + sqruff-lib 1 个），非本次跳过。

---

## 三、测试详情

### 3.1 libtest 逐目标结果（真机框架输出）

| 目标 | 结果 |
|------|------|
| sqruff-lib 单元测试 | ✅ 77 passed（+1 upstream ignore） |
| sqruff-lib-core 单元测试 | ✅ 30 passed |
| sqruff-sqlinference 单元测试 | ✅ 13 passed |
| lineage 单元测试 | ✅ 16 passed（+3 upstream ignore） |
| sqruff-lsp 单元测试 | ✅ 5 passed |
| sqruff-cli-lib 单元测试 | ✅ 8 passed |
| sqruff（bin）单元测试 | ✅ 0 passed（无单元用例） |
| ignore_data_directory（cli 集成） | ✅ 3 passed |
| verbose_logging_ignore（cli 集成） | ✅ 5 passed |
| sqruff-lib-dialects 单元测试 | ✅ 2 passed |
| **合计** | **✅ 159 passed / 0 failed / 4 ignored** |

### 3.2 harness=false 集成套件（按退出码判定，全部 rc=0）

crates/cli/tests 9 个：`ui`（lint 快照矩阵）/ `ui_github` / `ui_json` /
`fix_return_code` / `fix_parse_errors` / `config_not_found` / `configure_rule` /
`dialect_override` / `none_format`；
crates/lib/tests 2 个：`rules`（规则 fixture 套件，68 例 jinja 按上游开关跳过）/
`templaters`；crates/lib-dialects/tests 1 个：`dialects`。

### 3.3 消费者用例（test_package/test.sh，真实执行打包后 bin/sqruff）

| # | 用例 | 结果 |
|---|------|------|
| 1 | `sqruff --version` 输出 0.39.0，rc=0 | ✅ PASS |
| 2 | `sqruff --help` 列出 lint 子命令，rc=0 | ✅ PASS |
| 3 | 干净 SQL 文件 lint，rc=0 | ✅ PASS |
| 4 | 违规文件（LT01+LT12）lint，rc=1 且诊断含规则码 | ✅ PASS |
| 5 | `sqruff fix` 回环（修复后 re-lint 干净，文件内容正确） | ✅ PASS |
| 6 | `sqruff lsp` initialize 握手（stdio，含 capabilities，rc=0） | ✅ PASS |

---

## 四、关键问题分析

### 问题1: rules 套件 jinja 用例在无 Python 绑定平台连锁 panic（68 例）

**现象**：
```
thread '<unnamed>' panicked at crates/lib/tests/rules.rs:198:25:
Unsupported templater in case 'test_simple': Unknown templater 'jinja'.
Available templaters: raw, placeholder.
Set SQRUFF_SKIP_UNSUPPORTED_TEMPLATERS=1 to skip these tests.
error: test failed, to rerun pass `-p sqruff-lib --test rules`   # TEST_RC=101
```

**根因分析**：上游 jinja templater 由 pyo3 调用 Python 包实现
（`crates/lib/src/templaters/jinja.rs:22` `PyModule::import("sqruff.templaters.
jinja_templater")`）；上游 Makefile 的 rust_test 先 `uv run maturin develop`
安装该 Python 扩展。OHOS CLI 运行时不含 Python 绑定（feature 关闭），templater
注册表仅 raw/placeholder，rules.rs 对未知 templater 默认 panic。

**解决方案**：按 panic 信息自带的官方开关 `SQRUFF_SKIP_UNSUPPORTED_TEMPLATERS=1`
运行测试，68 个用例逐条打印 `Skipping case ...` 后跳过；未修改任何上游测试源、
未加 ignore、未伪造通过，跳过数量与原因在 MANIFEST.yml/notes 如实申报。
（本条已沉淀知识草稿 `knowledge/drafts/DRAFT-sqruff-0.39.0-rust-pyo3-jinja-templater-skip.*`，路径 B 知识贡献。）

### 问题2: conan-verify G2 因镜像注入下载超时（首轮 FAIL）

**现象**：
```
WARN: network: Error downloading file https://ghfast.top/https://github.com/...:
HTTPSConnectionPool(host='ghfast.top', port=443): Read timed out. (read timeout=60)
ERROR: sqruff/0.39.0@ohpcd/stable: Error in source() method
```

**根因分析**：G2 的 E017 预防会把 conandata.yml 中 `https://github.com` 前缀临时
改写为 ghfast.top 镜像；真机实测该镜像不可达（sexpect/2.4.0 2026-09-26 同款）。

**解决方案**：conandata.yml 改用 GitHub **官方 codeload 入口**
（`https://codeload.github.com/quarylabs/sqruff/tar.gz/refs/tags/v0.39.0`，
即 github.com archive URL 的官方 302 目标；真机重下 sha256
`af54cd921fa8565d69bec17678d6f38c6aa062acf5eb7d68fcdf9597d6372737` 逐字节一致）
+ 显式 `filename` 防 Conan 按 zip 误扩展名解码；codeload 官方域不受该前缀改写影响。

### 问题3: release+LTO 构建时间与 CI 超时预算

**现象**：`[profile.release] lto=true + codegen-units=1` 对每个 release 目标
生效，真机负载下 release 构建 ~28min，叠加测试编译后单次 conan create
保守估计 >3600s。

**解决方案**：`ci/config/build_timeouts.txt` 增加 `sqruff/0.39.0 10800`
（同类 Rust 件 alacritty/scooter/aiken/kingfisher 先例；条目置于文件中部的
Rust 条目簇，避免与 main 的尾部追加型条目产生 merge 冲突）；上游测试改为
`build()` 内执行（debug profile，与上游 Makefile 一致；单次 conan create
只编译一遍，test_package 仅重发计数）。本地 CI 与 W3 均实际读取到该预算
（`timeout --signal=KILL 10800 conan create`；2026-10-16 复跑 release 构建
实测 15m36s）。

### 问题4: test_package 就地运行导致上游源码解压污染仓库（首轮 CI JC 失败诱因之一）

**现象**：conan 就地运行 test_package conanfile（`self.build_folder` 即仓库内
`test_package/` 目录），首次实现将上游 tarball 解压到 `self.build_folder/upstream-src`，
在仓库工作树留下数千个文件（含 .github/.cargo 等隐藏文件），触发 CI JC5 junk 门禁风险。

**解决方案**（2026-10-16 修订后已结构性消除）：上游测试移入主配方 `build()`
执行、计数写入 conan 源目录 `res/` 并随包携带，test_package 不再做任何
下载/解压，仓库工作树零残留的成因被移除；CI 与 W3 复跑确认工作树干净、
JC5 通过（`git status` 干净）。

### 问题5: 平台 CI 因 bottle 固定 URL 404 失败（#93066/#93172，17-19s）

**现象**：
```
ERROR: sqruff/0.39.0: Error in build() method, line 367
	cargo = self._ensure_toolchain()
while calling '_unpack_bottles', line 231
	self._download_bottle(url, tgz)
	HTTPError: HTTP Error 404: Not Found
```

**根因分析**：worker 无本机 cargo，`build()` 走 Harmonybrew bottle 自举下载
`rust-1.98.1_1.arm64_ohos.bottle.tar.gz` —— 而 harmonybrew **bottle URL 只保留
每公式最新版**，固定版本 URL 必然随版本轮换 404（实测：旧 rust-1.97.1/1.98.1_1、
openssl@3 3.6.4 全部 404；现存活 rust-1.99.0、openssl@3 3.6.5）。源下载本身正常
（日志 `Sources correctly downloaded from codeload...`），与 git-clone/网络无关。

**解决方案**：弃用 bottle 自举，工具链改 **ohpcd 制品仓基础设施包**
`rust-toolchain/1.97.1`（`tool_requires`；版本不可变、零外链；tracexec/0.17.0、
below/0.11.0 先例），cargo 运行期 libssl/libcrypto 由 `openssl/3.5.6.1.1`
（`tool_requires`）静态 PIC 重链为私有 DSO（comet/0.3.2 先例；不写公共前缀）。
真机小验证：重链 libcrypto（5.2MB/7899 符号）+ 按需 binary-sign-tool 自签名后
`cargo 1.97.1`/`rustc 1.97.1` 均可执行；完整路径由 conan-verify G2 验证。

---

## 五、测试环境

```
OS: HarmonyOS HongMeng Kernel 1.12.0 (aarch64)
编译器: clang 15.0.4（OHOS SDK 26.0.0.18 / hnp worker 同版本）
Rust: rust 1.97.1 / cargo 1.97.1（ohpcd 制品仓 rust-toolchain/1.97.1
      tool_requires；cargo 运行库 = openssl/3.5.6.1.1 静态 PIC 重链私有 DSO）
构建: cargo --config target.aarch64-unknown-linux-ohos.linker=<cc> build
      --release --locked --bin sqruff（build() 内；CARGO_BUILD_JOBS=4）
测试: build() 内真实执行（计数硬门禁 + res/upstream_test_result.json 随包；
      test_package 重发 HMBS_UPSTREAM_TEST_RESULT 并硬校验）：
      SQRUFF_SKIP_UNSUPPORTED_TEMPLATERS=1 cargo test --locked -j 4 --no-fail-fast
      --workspace --exclude sqruff-cli-python --exclude sqruff-wasm --tests
上游源码: https://codeload.github.com/quarylabs/sqruff/tar.gz/refs/tags/v0.39.0
          sha256 af54cd921fa8565d69bec17678d6f38c6aa062acf5eb7d68fcdf9597d6372737
产物: bin/sqruff（NEEDED: libc.so only；PIE + GNU_RELRO + NX stack）
```

## 六、门禁结果

| 门禁 | 结果 |
|------|------|
| conan-verify G0–G4 / L2/L4/L5 | ✅ PASS（2026-10-16 工具链修订后重跑：G2 clean conan create 成功，含 build() 内上游全套测试与 test_package；reports/conan-verify-report.md） |
| test_package 消费者 | ✅ 6/6（HMBS_TEST_PACKAGE_RESULT passed:true） |
| 上游测试 HMBS marker | ✅ HMBS_UPSTREAM_TEST_RESULT status=passed, discovered/executed/passed=159, failed=0, ignored=4（build() 内真实执行；test_package 重发） |
| 本地 CI（ci/conan/build_and_test.sh） | ✅ PASS：L0/L1/L1e/L2/L4/L5 全过（JC 0 junk、JC6 单包合规、L1e 破坏性反证通过；2026-10-16 工具链修订后重跑） |
| W3（finish step 5/10） | ✅ PASS：`.ci-result.json` exit_code=0（log_sha256 4ab5b824…）；原始日志 archives/s/sqruff/0.39.0/reports/w3-local-ci.log |
| W4 独立审计 | ✅ 见 reports/audit-result.json（0 P0/P1；2026-10-16 复审） |

> 原始过程日志（conan-create.log / conan-verify-report.md / w3-local-ci.log）按仓库
> 评审规则 19 不随 PR 提交，保留于构建工作区；关键结论与哈希已在上表引用。

---

*报告生成时间: 2026-10-12（2026-10-16 定稿，含工具链修订后的重跑证据）*
