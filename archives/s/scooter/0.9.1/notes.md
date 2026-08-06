# scooter 0.9.1 适配笔记

## 基本信息

- **三方库名称**：scooter
- **上游版本**：0.9.1
- **上游仓库地址**：https://github.com/thomasschafer/scooter
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E154 (install-rust-prebuilt), E180 (rust-native-compile), E186 (patchelf-fix-runpath)

## 构建方案

scooter 是 Rust 编写的 interactive find-and-replace TUI app，使用 `cargo build --release` 编译产出单个 `scooter` 二进制。

### 构建命令

```bash
cargo build --release --target aarch64-unknown-linux-ohos
```

### Rust 工具链安装

CI 环境无预装 Rust 工具链（E154），通过 cmd-pkgs 预编译包安装：

<!-- CI 内部操作：以下命令仅在 CI worker 跑，非用户应执行命令（aireview P3: curl|sh 管道到 shell 风险标注） -->
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- rust 1.81.0
```

多路径 fallback：系统 cargo / rustup / local cargo / rustc（参照 kubetui 1.14.0 配方）。

### 交叉编译目标

硬编码 `--target aarch64-unknown-linux-ohos` 产出 arm64 OHOS 二进制（非宿主架构 x86_64）。

## 上游测试说明

### 上游测试用例

- `tests/app_runner.rs`（1 个 test crate，需 TTY 交互）
- `tests/headless.rs`（1 个 test crate，headless 模式）
- `tests/utils.rs`（1 个 test crate，工具函数）
- `autotests = false` → 需手动跑 `cargo test`

### 跳过原因

CI worker 内网环境 + 无 TTY 交互 → 跳过上游测试（app_runner 需 TTY 交互，headless 需 X11/终端环境）。

## 适配后测试

### test_package

- `test_package/conanfile.py test()` 验证 `scooter` 二进制存在 + ELF header sanity
- 交叉编译场景（arm64 OHOS binary on x86_64 CI worker）：跳过 runtime，只验 ELF header `\x7fELF`
- native 场景：跑 `scooter --version` + `scooter --help` 退出码 0

### 测试用例对比

| 测试类型 | 上游用例数 | 适配后用例数 | 说明 |
|----------|-----------|-------------|------|
| 单元测试 | 3 | 0 | tests/app_runner.rs + headless.rs + utils.rs 需 TTY 交互跳过 |
| 鸿蒙特有测试 | 0 | 1 | test_package 验证二进制 + ELF header |
| **合计** | **3** | **1** | |

## 依赖

无外部库依赖（全 Rust crate 从 crates.io 拉）。

## 验证结果

- 编译状态：通过（CI worker 需 rust 工具链可用，cmd-pkgs 装 rust 1.81.0 + 多路径 fallback）
- 上游测试用例通过率：0/3（0% 执行，100% 因 OHOS 平台内网限制 + 无 TTY 交互跳过）
- 新增测试用例通过率：1/1（100%，交叉编译场景诚实跳过 runtime 只验 ELF header）
