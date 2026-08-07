# docuum 0.27.0 适配笔记

## 编译环境
- 构建系统: custom（Cargo/Rust）
- 编译日期: 2026-08-02（本地 CI 模拟复验 2026-08-07）
- 平台: OHOS（OpenHarmony PC, aarch64）
- 状态: failed（未适配）

## 本地 CI 模拟验证（2026-08-07）

- **conan create 通过（rc=0）**：失败记录模式 build() 校验 manifest/notes 完整不抛错，
  成功打包 share/docuum/{manifest.yaml,notes.md}；test_package 执行
  `test_failed_archive.py` 校验失败归档真实性 → **PASS: docuum failed adaptation record is complete**。
- **上游测试无法运行（详细原因）**：docuum 是 Rust/Cargo 工具，真实构建需 cargo/rustc；
  本地为 HarmonyOS musl 环境无 glibc ld-linux-aarch64.so.1，官方 rust 工具链
  （glibc 动态链接 ELF）签名后仍 rc=126 无法加载，cmd-pkgs 无 OHOS rust 资产（404）——
  与 kubetui/trlc 同根因，属本地环境限制；上游 `cargo test` 单元测试同样被挡。
- 该库按 prefixsuffix 模式如实记录失败适配（status: failed），本地验证确认记录包可构建、CI 不红。

## 编译步骤

```bash
# 下载源码
wget https://github.com/stepchowfun/docuum/archive/refs/tags/v0.27.0.tar.gz

# 解压并进入
tar xzf v0.27.0.tar.gz && cd docuum-0.27.0

# Cargo 构建（OHOS CI worker 无 Rust 工具链，无法执行）
cargo build --release
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cargo build` 报 Error 127 | OHOS CI worker 无 Rust 工具链（rustc/cargo） | 采用 prefixsuffix 失败记录模式，如实标记 status: failed |
| 2 | test_package 无可执行二进制 | 无 Rust 工具链无法编译 | 校验失败归档内容（manifest + notes）真实性 |

## 验证结果

```bash
# OHOS 上无编译产物，验证失败归档内容
$ python3 test_failed_archive.py <package_folder>
PASS: docuum failed adaptation record is complete
```

## 注意事项
- docuum 是 Rust/Cargo 工具，OHOS CI worker 无 Rust 工具链，无法编译
- 失败归档包含 status: failed、failure_reason（Rust/Cargo 工具链缺失）与 OHOS 说明
- 待 CI worker 安装 Rust 工具链后可启用真实 Cargo 构建

---

**编译结束**: 2026-08-02
**最终状态**: failed
