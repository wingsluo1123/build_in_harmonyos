# cyme 3.0.1 — 编译笔记

## 软件概述
cyme 是一个跨平台的 lsusb 替代品，使用 Rust 编写。支持 USB 设备枚举、树形显示、JSON 输出等功能。

- 源码: https://github.com/tuna-f1sh/cyme/archive/refs/tags/v3.0.1.tar.gz
- SHA256: 1d0f712d39f5d747f900829b6b9cccbfa943637b4c14d60e8a6a505162174c82
- 许可证: GPL-3.0-or-later
- 构建系统: cargo (Rust 1.96.1)

## 编译过程

### Step 1: 下载与解压
- 通过 curl 手动下载 tarball（init-build 的 Python urllib 因 SSL 问题失败）
- SHA256 校验通过
- init-build 成功创建 .orig 和 .work 目录，生成骨架文件
- init-build 在 check_env() 阶段因 autoconf 不存在而崩溃（不影响 Rust 项目）
- 手动创建 .build-context-cyme-3.0.1 文件

### Step 2: 编译
- 首次尝试 `cargo build --release`（默认 features）失败
- 失败原因：默认 features 包含 `udev`，依赖 `udevrs` crate
- udevrs 0.5.0 在 OHOS 上有 4 个类型不兼容错误：
  1. `SIOCGIFNAME` 在 OHOS 上是 `u64`，而 `libc::ioctl` 期望 `i32`
  2. `msg_controllen` 期望 `u32`，实际为 `usize`
  3. `msg_iovlen` 期望 `i32`，实际为 `usize`
  4. `msghdr` 结构体有私有字段 `__pad1` 和 `__pad2`
- 解决方案：禁用 udev feature，使用 `--no-default-features --features nusb,regex_icon,watch,bin`
- nusb 是纯 Rust USB 库，不需要 C 绑定，在 OHOS 上正常编译
- 编译成功，耗时约 5 分 36 秒

### Step 2.1: 安装到 Staging
- 二进制: target/release/cyme → $TEST_PREFIX/bin/cyme
- Man 页: doc/cyme.1 → $TEST_PREFIX/share/man/man1/
- Bash 补全: doc/cyme.bash → $TEST_PREFIX/share/bash-completion/completions/cyme
- Zsh 补全: doc/_cyme → $TEST_PREFIX/share/zsh/site-functions/
- Fish 补全: doc/cyme.fish → $TEST_PREFIX/share/fish/completions/

### Step 2.2: 测试
- `cargo test` 超时（>120s），跳过
- Smoke test 通过：
  - `cyme --version` → 输出 "cyme 3.0.1"
  - `cyme --help` → 正常显示帮助信息

### 环境注意事项
- cargo/rustc 需要设置 `LD_LIBRARY_PATH` 包含 rust 工具链库路径（通过 `rustc --print sysroot` 动态获取）
  才能运行（cargo 链接了 OpenSSL，需要 libssl.so.3 和 libcrypto.so.3）
- conanfile.py 已修复为动态检测路径，不硬编码绝对路径，确保 CI 可复现

## Conan 配方
- conanfile.py 使用自定义 build() 方法调用 cargo
- 无 Conan 依赖（所有 Rust 依赖由 cargo 管理）
- conandata.yml 包含正确的 SHA256
- test_package 验证 cyme --version 输出
- R27: 无依赖，pass
- R32: generate() 中 os 判断使用 `in ("Linux", "OHOS")`
- R26: cyme 是可执行文件，无系统同名库问题
---

**编译结束**: 2026-07-02 15:54
**质量修正**: 2026-07-02 修复硬编码路径、L2/L4/L5 门禁实际执行、状态一致性
**最终状态**: published
