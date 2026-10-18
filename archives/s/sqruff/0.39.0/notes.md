# sqruff 0.39.0 适配笔记

## 编译环境
- 构建系统: cargo（Rust workspace，edition 2024，MSRV 1.96；Cargo.lock 共 240
  个 package —— 10 个 workspace 成员 + 230 个 registry crate，0 个 git 依赖）
- 编译日期: 2026-10-12（2026-10-16 工具链与测试架构修订）
- 编译器: clang/clang++ 15.0.4（OHOS SDK）；Rust 工具链 = ohpcd 制品仓
  `rust-toolchain/1.97.1` 基础设施包（tool_requires；cargo/rustc 私有拷贝 +
  按需 binary-sign-tool 自签名；tracexec/0.17.0、below/0.11.0、comet/0.3.2 先例）；
  cargo 运行库 = `openssl/3.5.6.1.1` 静态 PIC 重链私有 DSO（零外链）
- 状态: built

## 编译步骤

sqruff 是高性能 SQL linter 与格式化器（SQLFluff 的 Rust 重写），单一 CLI
二进制 `sqruff`（lint/fix/parse/rules/templaters/lsp 子命令；LSP 内嵌于同一
二进制，无独立 sqruff-lsp 可执行文件）：

```bash
# 工具链：制品仓 rust-toolchain/1.97.1（tool_requires）——cargo/rustc 复制到
# 构建目录私有副本，探测失败才用 binary-sign-tool 自签名；cargo 运行期的
# libssl/libcrypto 由 openssl/3.5.6.1.1 静态 PIC 重链为私有 DSO 并加入
# LD_LIBRARY_PATH（不写任何公共前缀）
cargo --config target.aarch64-unknown-linux-ohos.linker=<cc> build \
  --release --locked --bin sqruff            # build() 阶段，真机 ~28min
# 上游测试（build() 内执行，计数硬门禁写入 res/upstream_test_result.json；
# test_package 重发 HMBS 标记并硬校验计数；tracexec/0.17.0 范式）：
SQRUFF_SKIP_UNSUPPORTED_TEMPLATERS=1 cargo test --locked -j 4 --no-fail-fast \
  --workspace --exclude sqruff-cli-python --exclude sqruff-wasm --tests
```

配方要点：
- `source()`：`get()` 下载 GitHub 官方 codeload tag 归档 v0.39.0.tar.gz 并 strip_root
- `build_requirements()`：`tool_requires("rust-toolchain/1.97.1")` +
  `tool_requires("openssl/3.5.6.1.1")`（均来自 ohpcd 制品仓，零外链）
- `build()`：私有工具链拷贝（探测失败才 binary-sign-tool 自签名）→ openssl
  静态 PIC 重链私有 DSO → 私有 CARGO_HOME 配置（rsproxy.cn sparse +
  multiplexing=false + CA）→ `cargo build --release --locked --bin sqruff`
  → 上游全套测试（debug；解析真实 "test result:" 行 + failed==0/passed==159
  硬门禁 + 9 个 harness=false 目标 Running 行断言）→ 产物自签名 → bin/
- `package()`：`bin/sqruff` + `licenses/LICENSE` + `res/upstream_test_result.json`
- test_package `test()`：`/bin/sh test.sh`（6 个消费者用例，输出
  HMBS_TEST_PACKAGE_RESULT）→ 从包内 res/ JSON 重发 HMBS_UPSTREAM_TEST_RESULT
  并硬校验计数（failed==0、passed==159）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cargo test` 在 rules 套件大规模 panic（TEST_RC=101）：`Unsupported templater in case '...': Unknown templater 'jinja'. Available templaters: raw, placeholder` | 上游 jinja templater 由 pyo3 调用 Python 包 `sqruff.templaters.jinja_templater` 实现（crates/lib/src/templaters/jinja.rs:22）；上游 Makefile 先 `uv run maturin develop` 安装该 Python 绑定，Bazel/CI 亦然；OHOS CLI 运行时无 Python 绑定（feature 关闭），注册表仅 raw/placeholder | 使用 panic 信息自带的官方开关 `SQRUFF_SKIP_UNSUPPORTED_TEMPLATERS=1`：68 例 jinja 相关 case 逐条打印 `Skipping case ...` 后跳过。不改上游测试源、删除断言或伪造通过；其余 159 个 libtest 用例与全部 harness=false 集成套件真机全过 |
| 2 | release 档测试编译极慢（每个测试二进制都带 fat LTO，>1h 未完成） | `[profile.release] lto=true` + `codegen-units=1` 对测试目标同样生效 | test_package 上游测试改用 debug（与上游 Makefile `cargo test` 默认一致）：真机冷编译 ~16min + 全量执行 ~12min |
| 3 | 首轮测试未跑完其余目标就停止 | `cargo test` 默认在首个失败 target 即停 | 测试命令对齐上游 Makefile 增加 `--no-fail-fast`，一遍看到全部结果 |
| 4 | `conan-verify` G2 首轮 FAIL：`source()` 下载 `ghfast.top` Read timeout | G2 的 E017 预防把 conandata.yml 中 `https://github.com` 前缀临时改写为 ghfast.top 镜像，真机该镜像不可达（sexpect/2.4.0 2026-09-26 同款先例） | conandata.yml 改用 GitHub 官方 **codeload** 入口（`github.com/.../archive/...` 的官方 302 目标；真机重下 sha256 逐字节一致 `af54cd92...`）+ 显式 `filename` 防 Conan 按 zip 误判；codeload 官方域不受该前缀改写影响 |
| 5 | 平台 CI（#93066/#93172）`conan-build-test` 17-19s 即 FAIL：`build()` → `_unpack_bottles()` → `urllib.request.urlretrieve` **HTTP 404**（`rust-1.98.1_1.arm64_ohos.bottle.tar.gz`） | harmonybrew **bottle URL 只保留每公式最新版**，固定版本会 404（实测：旧 rust-1.97.1/1.98.1_1 与 openssl@3 3.6.4 均 404；现存活 rust-1.99.0、openssl@3 3.6.5）。worker 无本机 cargo，必走自举下载 → 404 必挂 | **弃用 bottle 自举**：工具链改用 ohpcd 制品仓 `rust-toolchain/1.97.1`（`tool_requires`；版本不可变、零外链；tracexec/0.17.0、below/0.11.0 已合入先例）；cargo 运行库改用 `openssl/3.5.6.1.1`（`tool_requires`）静态 PIC 重链为私有 DSO（comet/0.3.2 已合入先例；不写公共前缀，R49）。真机小验证：重链 libcrypto（5.2MB/7899 符号）+ 自签名 cargo/rustc 后 `cargo 1.97.1`/`rustc 1.97.1` 均可执行 |
| 6 | test_package 阶段二次编译（release+LTO 或 debug 全量）使单次 CI 成本 ~25min 且 HMBS 依赖重编译 | 旧架构：上游测试在 test_package 重下 tarball 后重编译执行 | 上游测试移入 `build()` 真实执行（计数从 "test result:" 行解析 + failed==0/passed==159 硬门禁，写 res/upstream_test_result.json 随包），test_package 只做消费者用例 + 重发 `HMBS_UPSTREAM_TEST_RESULT` 并硬校验计数（tracexec/0.17.0 范式）—— 单次 conan create 只编译一遍 |

## 源码修改

无补丁（`patches/` 为空，conandata.yml `patches: {}`）：OHOS 适配全部通过
构建环境配置（.cargo/config.toml 的链接器/镜像/网络容错）与上游官方测试
开关完成，未修改上游任何源文件。

## 依赖版本

- Rust 工具链：ohpcd 制品仓 `rust-toolchain/1.97.1`（`tool_requires`；cargo/rustc
  1.97.1 + aarch64-unknown-linux-ohos 标准库；宿主与目标一致）
- cargo 运行库：ohpcd 制品仓 `openssl/3.5.6.1.1`（`tool_requires`；静态 PIC
  重链为私有 DSO，仅本包 LD_LIBRARY_PATH 可见）
- Rust crate 依赖：Cargo.lock 固定（240 个 package：10 个 workspace 成员 +
  230 个 registry crate；无 git 依赖，经 rsproxy.cn sparse 镜像拉取）
- 无 C/C++ 三方库依赖（conanfile `requires` 为空）

## 上游测试清点（R51 申报表）

| 检查项 | 命令/依据 | 结果 |
|---|---|---|
| libtest 目标数 | 真机 `cargo test` 输出 `Running unittests ...` | 8 |
| libtest 用例数 | `test result:` 行求和 | 159 passed / 0 failed / 4 ignored（上游自带）/ 0 filtered |
| harness=false 目标 | crates/cli/tests 9 + crates/lib/tests 2 + crates/lib-dialects/tests 1 | 12 个，全部 exit 0（逐 case 断言真实执行） |
| jinja 模板器用例 | 上游开关 `SQRUFF_SKIP_UNSUPPORTED_TEMPLATERS=1` | 68 例跳过（`Skipping case ...` 计数；平台无 pyo3/Python 绑定） |
| doc-tests | `--tests` 排除（工具链无 rustdoc）；静态核对 crates/*.rs 文档块共 5 对（1 对 ` ```ignore `、4 对 ` ```sql `），0 个可执行 doctest；sqruff-lib 显式 `doctest=false` | 0 用例受影响 |
| 排除的 crate | sqruff-cli-python（pyo3/maturin 绑定）、sqruff-wasm（wasm32 绑定） | 平台绑定 crate，非 OHOS CLI 运行时组件 |
| 通过率 | libtest 159/159；12 个集成套件二进制全绿 | 100%（不含上游自带 ignore 与 jinja 平台跳过） |

## 交付物

| 文件 | 说明 |
|------|------|
| bin/sqruff | SQL linter/formatter CLI（静态链接 ELF，`readelf` NEEDED 仅 libc.so；PIE + GNU_RELRO + NX stack） |

## 验证结果

- release 构建（真机，W3 复跑 2026-10-16）：15m36s（与设备上其他并行构建共享 8 核）
- 上游测试（build() 内真实执行，rust-toolchain 1.97.1）：159 libtest 全过
  （4 upstream-ignored、0 filtered），12 个 harness=false 套件全过；
  HMBS_UPSTREAM_TEST_RESULT status=passed
- 消费者用例（test_package）：6/6（HMBS_TEST_PACKAGE_RESULT passed:true）
- conan-verify（2026-10-16 工具链修订后重跑）：G0–G4 + L2/L4/L5 全 PASS
  （报告 reports/conan-verify-report.md）
- 本地 CI / W3（finish step 5/10 重跑）：L0/L1/L1e/L2/L4/L5 全 PASS；
  `.ci-result.json` exit_code=0（log_sha256 4ab5b824…；原始日志
  reports/w3-local-ci.log）
- W4 独立审计：reports/audit-result.json（0 P0/P1）

## 注意事项

- `sqruff lsp` 为同一二进制的子命令（LSP 服务器，stdio 传输）；本包
  不安装 Python/wasm 平台绑定（与上游 x86_64 二进制发布口径一致）。
- 设备 HMFS/HMDFS 与 OHOS /tmp 只读：配方构建的 TMPDIR 指向构建目录内 tmp/
  （或 HMBS_TMPDIR）。
- 工具链与 cargo 运行库全部来自制品仓（rust-toolchain/1.97.1、
  openssl/3.5.6.1.1）；**不使用任何 harmonybrew bottle 下载**——bottle URL
  只保留每公式最新版，固定版本 URL 必然随版本轮换而 404（2026-10-15 CI 实测）。
- 共享设备：构建 CARGO_BUILD_JOBS=4（资源耗尽类错误自动降 1 重试一次）；
  CI 超时预算通过 `ci/config/build_timeouts.txt` 显式设置 10800s。

**编译结束**: 2026-10-16
**最终状态**: built（conan-verify G0–G4/L2/L4/L5、本地 CI/W3（.ci-result.json exit_code=0，log_sha256 4ab5b824…）与 W4 审计（0 P0/P1）全部通过）
