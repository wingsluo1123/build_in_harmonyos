# codebook-lsp 0.3.41 适配笔记

## 编译环境
- 构建系统: Rust/Cargo (edition 2024, custom build)
- 编译日期: 2026-07-02
- 编译器: rustc (Rust toolchain, aarch64-unknown-linux-ohos target)
- 状态: built

## 编译步骤

codebook-lsp 是一个 Rust 编写的代码感知拼写检查器，包含 LSP 语言服务器实现。
项目使用 Cargo workspace 管理，包含 codebook、codebook-config、codebook-lsp、
downloader、dictionary-builder 五个 crate。

### 1. 环境准备

设置 OpenSSL 和构建工具环境变量：

```bash
export HARMONBREW="/storage/Users/currentUser/.harmonybrew"
export LD_LIBRARY_PATH="$HARMONBREW/lib:${LD_LIBRARY_PATH:-}"
export PKG_CONFIG_PATH="$HARMONBREW/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
export OPENSSL_DIR="$HARMONBREW"
export OPENSSL_LIB_DIR="$HARMONBREW/lib"
export OPENSSL_INCLUDE_DIR="$HARMONBREW/include"
export OPENSSL_STATIC=1
```

### 2. 源码获取与解压

从 GitHub 下载 v0.3.41 源码包并解压。由于网络限制，GitHub 下载超时，
需通过代理或镜像重试。

### 3. 应用 cargo registry 补丁

构建前需对 cargo registry 中的依赖 crate 打补丁：
- nix 0.26.4: 修补 5 个源文件解决 OHOS 平台兼容性问题
- aws-lc-sys 0.41.0: 修补 builder/cmake_builder.rs 和 aws-lc/CMakeLists.txt
  解决 CMake 无法检测 OHOS 平台处理器架构的问题

### 4. 编译

```bash
cd $BUILD_SRC_DIR
cargo build --release --locked -p codebook-lsp
```

cargo build 流程：
1. Cargo 解析 Cargo.lock，下载所有依赖 crate 到 registry
2. 编译依赖链（按拓扑序），包括 aws-lc-sys（CMake 子构建）、nix、openssl-sys 等
3. 编译 codebook-lsp 二进制
4. 链接生成 target/release/codebook-lsp

### 5. 安装与验证

```bash
# 验证二进制可用
./target/release/codebook-lsp --version
# 输出: codebook-lsp 0.3.41

# 运行测试
cargo test --release
# 结果: 13 passed
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 源码下载超时 (SSL EOF) | OHOS 环境访问 GitHub 不稳定，SSL 连接被中断 | 多次重试下载，或通过镜像源获取 tarball；conan create 阶段同样受影响 |
| 2 | Cargo 编译 openssl-sys 报符号缺失 | openssl-sys 链接系统 OpenSSL 时找不到部分符号，OHOS 的 OpenSSL 构建与标准 Linux 有差异 | 设置 OPENSSL_DIR 指向 harmonybrew 安装的 OpenSSL，强制使用正确的库路径 |
| 3 | openssl-sys pkg-config 失败 | PKG_CONFIG_PATH 未包含 harmonybrew 的 pkgconfig 目录，pkg-config 找不到 openssl.pc | 显式设置 PKG_CONFIG_PATH 包含 $HARMONBREW/lib/pkgconfig |
| 4 | nix 0.26.4 编译失败（8 个错误） | nix crate 在 OHOS 平台上有兼容性问题，部分 syscall 常量和结构体在 OHOS 内核头文件中缺失或定义不同 | 修补 nix 0.26.4 的 5 个源文件（fcntl.rs, sys/signal.rs, sys/statfs.rs, sys/statvfs.rs, Cargo.toml），适配 OHOS 平台差异 |
| 5 | aws-lc-sys 汇编符号未定义 (ld.lld undefined symbol) | aws-lc 的 CMake 无法检测 CMAKE_SYSTEM_PROCESSOR（OHOS 未被 CMake 识别为已知平台），ARCH 被设为 "generic"，跳过所有汇编源文件，但 C 代码仍引用 asm 符号（ChaCha20_ctr32_neon, bn_mul_mont, aes_hw_encrypt 等） | 修补 aws-lc/CMakeLists.txt 强制设置 CMAKE_SYSTEM_PROCESSOR=aarch64 和 ARCH=aarch64；修补 cmake_builder.rs 添加 configure_open_harmony() 方法设置 CMAKE_SYSTEM_NAME=Linux 和 OHOS_ARCH |

## 源码修改

### nix 0.26.4 补丁（cargo registry）

补丁文件: `patches/0001-nix-ohos-compat.patch`

修改的文件（5 个）：
1. **Cargo.toml** — 添加 OHOS target 平台声明
2. **src/fcntl.rs** — 修复 fcntl 相关常量在 OHOS 上的缺失
3. **src/sys/signal.rs** — 适配 OHOS 信号处理差异（SIGCLD vs SIGCHLD 等）
4. **src/sys/statfs.rs** — 修复 statfs 结构体字段在 OHOS 上的差异
5. **src/sys/statvfs.rs** — 修复 statvfs 结构体字段在 OHOS 上的差异

### aws-lc-sys 0.41.0 补丁（cargo registry）

补丁文件: `patches/0002-aws-lc-sys-cmake-arch.patch`

修改的文件（2 个）：
1. **builder/cmake_builder.rs** — 添加 `configure_open_harmony()` 方法：
   - 当 `target_env() == "ohos"` 时调用
   - 设置 `CMAKE_SYSTEM_NAME=Linux` 和 `CMAKE_SYSTEM_PROCESSOR=aarch64`
   - 设置 `OHOS_ARCH=arm64-v8a`（针对 aarch64-unknown-linux-ohos target）
   - 查找 OHOS NDK/SDK toolchain 文件
   - 设置正确的 CFLAGS/CXXFLAGS/ASMFLAGS

2. **aws-lc/CMakeLists.txt** — 修改 ARCH 检测逻辑：
   - 在处理器检测前添加 `if(NOT CMAKE_SYSTEM_PROCESSOR) set(CMAKE_SYSTEM_PROCESSOR "aarch64") endif()`
   - 在 ARCH 匹配的 else 分支添加 OHOS 平台回退逻辑
   - 确保 ARCH 正确设为 aarch64 而非 generic

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| Rust toolchain | stable (edition 2024) | aarch64-unknown-linux-ohos target |
| openssl (harmonybrew) | 3.x | 通过 harmonybrew 安装，提供 libssl.a/libssl.so |
| aws-lc-sys | 0.41.0 | cargo 依赖，需打补丁 |
| nix | 0.26.4 | cargo 依赖，需打补丁 |
| rustls | <0.24 | TLS 库，使用 aws-lc-rs 后端 |
| clang | 15 | OHOS 平台 C/C++ 编译器（用于 aws-lc CMake 子构建） |

## 验证结果

```bash
# 二进制版本验证
$ ./target/release/codebook-lsp --version
codebook-lsp 0.3.41

# 单元测试
$ cargo test --release
running 13 tests
test result: ok. 13 passed; 0 failed; 0 ignored; 0 measured

# 链接器无未定义符号
$ cargo build --release -p codebook-lsp 2>&1 | grep -c undefined
0
```

## 注意事项

1. **cargo registry 补丁是临时的**：cargo 重新下载依赖时会覆盖补丁。在 conan 构建中，
   需要在 build() 方法中通过 cargo patch 或在构建前手动应用 patches/ 目录中的补丁文件。
   补丁应用时机：cargo fetch 之后、cargo build 之前。

2. **GitHub 网络问题**：OHOS 环境访问 GitHub 不稳定，conan create 的 source() 下载
   可能失败。建议在 conanfile.py 中添加备用下载源或使用本地缓存的 tarball。

3. **CMake 子构建**：aws-lc-sys 内部使用 CMake 构建 aws-lc C 库，需要 cmake 可用且
   正确设置 OHOS 工具链。补丁通过设置 CMAKE_SYSTEM_NAME=Linux 绕过 CMake 对 OHOS
   平台的未知检测。

---

**编译结束**: 2026-07-02 15:17
**最终状态**: built
