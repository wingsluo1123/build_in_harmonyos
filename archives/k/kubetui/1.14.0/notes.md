# kubetui 1.14.0 适配笔记

## 编译环境
- 构建系统: cargo
- 编译日期: 2026-07-31（本地 CI 模拟复验 2026-08-07）
- 编译器: Rust (rustc 1.81.0)
- 状态: failed

## 本地 CI 模拟验证（2026-08-07）

### 已实证项
1. **源码完整性**：conan 缓存源码版本确认 1.14.0（Cargo.toml version=1.14.0），
   Cargo.lock 完整；上游 `src/` 内嵌 **538 个 #[test] 单元测试**（cargo test 可跑），
   `test/` 目录为 k8s rbac 集成测试配置（需真实集群，CI 无法运行）。
2. **rust 组件下载**：static.rust-lang.org 官方源下载 rustc/cargo 1.81.0
   （aarch64-unknown-linux-gnu）+ rust-std-1.81.0-aarch64-unknown-linux-ohos 组件，
   sha256 全部与配方一致（rustc=08acb66f…、cargo=00c5185b…、std=2f6034e5…）。

### 本地无法运行项及详细原因（cargo build / cargo test 均无法执行）
- **根因：本地为 HarmonyOS musl 环境，官方 rust 工具链是 glibc 动态链接二进制，无法加载**：
  - `file` 显示官方 rustc/cargo 为 `ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-linux-aarch64.so.1)`；
  - 本地 `/lib/` 只有 `ld-musl-aarch64.so.1`（musl loader），**无 glibc 的 ld-linux-aarch64.so.1**；
  - 对 rustc 签名（binary-sign-tool sign 成功写入 .codesign）后仍报
    `sh: ./rustc_signed: No such file or directory`（rc=126，动态链接器缺失，非权限问题）；
  - cmd-pkgs 无 OHOS 专用 rust 预编译资产（`rust-1.81.0-ohos-aarch64.tar.gz` 404），
    本地 rustup-init 为 sh 脚本且不可执行。
  - 属**本地模拟环境限制**，非配方缺陷：配方逻辑（组件包 sha256 校验→合并 rust_root→
    `cargo build --release --target aarch64-unknown-linux-ohos`）在具备可运行 rust 工具链的
    CI worker 上可执行。
- **上游 538 个单元测试**：需 `cargo test`（同样依赖可运行的 rustc），被上述环境限制挡住，
  本地无法运行；`test/` rbac 集成测试还需真实 k8s 集群。

## 编译步骤

```bash
cargo build --release --target aarch64-unknown-linux-ohos
```

## 遇到的问题与解决方案

- Rust 工具链通过 cmd-pkgs 预编译包安装（E154 知识条目）
- 上游 test/ 目录的 rbac 集成测试需要真实 Kubernetes 集群，CI 中无法运行

## 依赖版本

无外部 C/C++ 依赖，Rust crate 由 cargo 管理

## 验证结果

```bash
./target/aarch64-unknown-linux-ohos/release/kubetui --help
```
