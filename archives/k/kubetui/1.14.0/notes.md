# kubetui 1.14.0 适配笔记

## 编译环境
- 构建系统: cargo
- 编译日期: 2026-07-31
- 编译器: Rust (rustc 1.81.0)
- 状态: failed

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
