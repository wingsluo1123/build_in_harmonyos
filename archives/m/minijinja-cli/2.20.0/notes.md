# 编译笔记 - minijinja-cli 2.20.0

## 编译状态：成功（Conan 配方验证通过）

## 编译信息

- **软件名称**: minijinja-cli
- **版本**: 2.20.0
- **编译日期**: 2026-08-06
- **构建系统**: Cargo (Rust)
- **源码来源**: GitHub (mitsuhiko/minijinja)
- **SHA256**: 2cde511df6486d8c2bda050d3f26c504796448a15e7ea50ede2ab75373129430

## 编译过程

### 1. 环境准备

- 安装 Rust 工具链 (rustc 1.97.1) via Harmonybrew
- 配置 cargo 镜像源 (rsproxy.cn) 解决 crates.io 不可达问题
- 设置 cc -> clang 符号链接 (Rust cc-rs crate 需要 cc 命令)

### 2. 源码获取

- 从 GitHub 下载 minijinja-2.20.0.tar.gz (通过 gh-proxy.com 镜像)
- 工作区包含 minijinja, minijinja-cli, minijinja-contrib 等多个 crate

### 3. 编译适配

#### 问题：rustyline TIOCGWINSZ 类型不匹配

OHOS 平台上 `libc::TIOCGWINSZ` 定义为 `u64`，但 `libc::ioctl` 期望 `c_int` (i32)。
rustyline 14.0.0 使用 `nix::ioctl_read_bad!` 宏直接传递 `TIOCGWINSZ`，导致类型不匹配。

**修复方案**：在 cargo fetch 下载依赖后，将 `nix::ioctl_read_bad!` 宏调用替换为
直接调用 `libc::ioctl` 并将 `TIOCGWINSZ` 显式转换为 `c_int`。

```rust
// 原始代码:
nix::ioctl_read_bad!(win_size, libc::TIOCGWINSZ, libc::winsize);

// 修复后:
unsafe fn win_size(fd: libc::c_int, data: &mut libc::winsize) -> nix::Result<libc::c_int> {
    let ret = libc::ioctl(fd, libc::TIOCGWINSZ as libc::c_int, data as *mut _ as *mut libc::c_void);
    nix::errno::Errno::result(ret)
}
```

#### 问题：cargo 无法访问 crates.io

crates.io 返回 403，使用 rsproxy.cn 镜像源替代。

#### 问题：cc 命令不存在

OHOS 系统有 clang 但没有 cc 符号链接。conanfile.py 自动创建 cc -> clang 符号链接。

### 4. Conan 配方生成

创建 conanfile.py + conandata.yml + test_package/ 完整 Conan 配方：
- `package_type = "application"` (命令行工具)
- `build()` 方法自动安装 Rust 工具链（如 CI worker 未安装）
- `build()` 方法自动创建 cc 符号链接
- `build()` 方法自动修复 rustyline OHOS 兼容性问题
- `test_package/` 包含 smoke test (--version + 模板渲染)

### 5. 验证结果

- conan create: ✅ 通过
- test_package: ✅ 通过
  - minijinja-cli --version: 输出 "minijinja-cli 2.20.0" ✅
  - 模板渲染: 功能验证通过 ✅
- 本地 CI 模拟 (build_and_test.sh): ✅ 通过
---

**编译结束**: 2026-08-07 00:38
**最终状态**: built
