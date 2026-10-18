# DRAFT-sqruff-0.39.0-rust-pyo3-jinja-templater-skip

## 症状

无 Python 绑定的平台（OHOS 真机/CI，pyo3 feature 关闭）上执行 sqruff 上游测试套件，
`crates/lib/tests/rules.rs`（harness=false）对 `templater = jinja` 的 fixture 用例全部
panic 连锁失败（首轮 68 例）：

```
thread '<unnamed>' panicked at crates/lib/tests/rules.rs:198:25:
Unsupported templater in case 'test_simple': Unknown templater 'jinja'.
Available templaters: raw, placeholder.
Set SQRUFF_SKIP_UNSUPPORTED_TEMPLATERS=1 to skip these tests.
...
error: test failed, to rerun pass `-p sqruff-lib --test rules`   # TEST_RC=101
```

## 根因

- 上游 sqruff 的 jinja templater 是 **pyo3/Python 绑定**实现：`crates/lib/src/
  templaters/jinja.rs:22` `PyModule::import(py, "sqruff.templaters.jinja_templater")`。
- 上游 Makefile `rust_test` 先 `uv run maturin develop` 安装该 Python 扩展，GitHub
  Bazel CI 同样先构建 Python 绑定；即其测试环境隐含“Python 绑定可用”。
- OHOS CLI 运行时不含 Python 绑定（feature 关闭），`Linter::get_templater` 对
  templater=jinja 返回 `Unknown templater`；rules.rs 对未知 templater 默认
  panic，panic 文本自带官方开关提示（`SQRUFF_SKIP_UNSUPPORTED_TEMPLATERS`）。

## 修复（本次采用）

按 panic 信息自带的**上游官方开关**运行测试，用例逐条打印 `Skipping case ...`
后跳过；不改上游测试源、不加 ignore、不伪造通过：

```bash
SQRUFF_SKIP_UNSUPPORTED_TEMPLATERS=1 cargo test --locked -j 4 --no-fail-fast \
  --workspace --exclude sqruff-cli-python --exclude sqruff-wasm --tests
```

真机实测（2026-10-12，HarmonyOS aarch64）：
- 无开关：`-p sqruff-lib --test rules` panic，rc=101；
- 有开关：159 libtest 用例全过 + 12 个 harness=false 集成套件 rc=0，
  68 行 `Skipping case`（jinja 用例），`TEST_RC=0`。

如实申报：跳过数量与原因写入 `test_package/MANIFEST.yml`（上游测试审计）、
`notes.md` 与 PR 正文“上游测试用例修改说明/补充说明”。

## 适用范围

- 任何把部分功能委托给 pyo3/Python 绑定、且上游测试覆盖该功能的 Rust crate
  （templaters / Python 扩展 / plugin 类），在无 Python 绑定的设备或 CI 上跑
  `cargo test` 即触发同类 panic；
- 与包规模无关，取决于测试集中是否存在这类用例。

## 反例/边界

- 非本机理的测试失败：断言/编译失败有各自报错面（无 "Unknown templater" panic）；
- 必须使用**上游提供的**跳过开关；上游没有开关时，应如实上报平台不支持的用例
  数量与原因，而不是删除测试或加 `#[ignore]`；
- 若未来 OHOS 具备 pyo3/Python 绑定环境（maturin 构建上游 Python 包），这些用例
  可全量执行（兜底路线，成本高，非默认）。

## 触发实例

- sqruff/0.39.0（2026-10-12）：真机首轮 `cargo test` 在 rules 套件 panic 68 例
  （TEST_RC=101）→ 设置上游开关后全绿并如实申报。

## 相关

- `DRAFT-rust-toolchain-no-rustdoc-skip-doctests`：同为“平台能力缺失下的显式取舍 +
  如实申报”族（rustdoc 缺失排除 doc-tests 阶段；本条为 Python 绑定缺失跳过 jinja
  用例）。
- `DRAFT-ohos-rust-cargo-no-toolchain` / `DRAFT-ohos-cargo-no-http2-sparse-multiplexing`：
  Rust/cargo on OHOS 工具链族，本条是“上游功能子集依赖 Python 绑定”面的补充。
