# sqruff — 高性能 SQL linter 与格式化器

`sqruff` 是用 Rust 编写的高性能 SQL 代码检查（lint）与格式化工具
（上游 `quarylabs/sqruff`，SQLFluff 的 Rust 重写）。它提供可配置的
SQL lint 规则集（dialect 感知）、自动修复（fix）、格式化、语法解析、
规则与模板器查询，并内嵌 LSP 服务器（`sqruff lsp`）供编辑器接入。

## 主要功能

- `sqruff lint`：对文件/目录/标准输入执行 SQL lint，支持 human /
  json / github-action 等输出格式与 `--dialect`、`-c/--config`。
- `sqruff fix`：自动修复可修复的 lint 违规（返回码语义：全修复=0、
  部分修复=1）。
- `sqruff format / parse / rules / templaters / info`：格式化、解析
  检查与规则/模板器信息。
- `sqruff lsp`：stdio 传输的 LSP 服务器（内嵌于同一二进制）。

## OHOS 适配要点

- **Rust/cargo 构建**：`cargo build --release --locked`（`--bin sqruff`）。
  上游 Cargo.lock 与 tag 归档完全一致，`--locked` 保证零版本漂移。
- **零源码补丁**：OHOS 适配全部通过构建环境配置完成 —— 链接器（clang）、
  crates.io 镜像（rsproxy.cn sparse）、网络容错配置，未修改上游任何源文件。
- **工具链（制品仓，零外链）**：构建工具链与运行库全部来自 ohpcd 制品仓——
  `rust-toolchain/1.97.1`（cargo/rustc + OHOS aarch64 标准库；私有拷贝 + 按需
  binary-sign-tool 自签名）与 `openssl/3.5.6.1.1`（静态 PIC 重链私有 DSO，
  cargo 运行期 libssl/libcrypto）；设备与 CI（clean 环境）行为一致
  （tracexec/0.17.0、below/0.11.0、comet/0.3.2 先例）。
- **上游测试**：`build()` 内真实执行
  `SQRUFF_SKIP_UNSUPPORTED_TEMPLATERS=1 cargo test --locked -j 4 --no-fail-fast
  --workspace --exclude sqruff-cli-python --exclude sqruff-wasm --tests`
  （排除需要 Python/wasm 工具链的平台绑定 crates；`--tests` 排除无 rustdoc
  的 doc-tests 空阶段；68 例 jinja/pyo3 用例按上游官方开关跳过并如实申报），
  计数硬门禁（failed==0、passed==159）并随包携带；test_package 重发
  HMBS 标记并硬校验，另含 6 个消费者用例。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/sqruff` | 命令行工具（lint/fix/format/parse/rules/lsp）；单一二进制 |

## 依赖关系

- 编译依赖（conan `tool_requires`，均在 ohpcd 制品仓）：`rust-toolchain/1.97.1`
  与 `openssl/3.5.6.1.1`；Rust crate 依赖由上游 Cargo.lock 管理（经 rsproxy.cn
  镜像拉取）。零外部 URL 依赖。
- 运行依赖：仅 OHOS 系统库（libc 等，`/system/lib64` 自带）。

## 参考资料

- 上游仓库：<https://github.com/quarylabs/sqruff>
- 许可证：Apache-2.0
