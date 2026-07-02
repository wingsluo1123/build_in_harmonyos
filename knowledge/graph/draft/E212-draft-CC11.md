# E212 — aws-lc-rs assembly symbols undefined on OHOS due to CMake processor detection failure

## 错误特征

当 Rust 项目使用 rustls + aws-lc-rs（通过 aws-lc-sys crate）在 OHOS 平台上编译时，
链接阶段会报大量 `ld.lld: error: undefined symbol` 错误，涉及的符号均为汇编实现
的加密函数：

```
ld.lld: error: undefined symbol: aws_lc_ChaCha20_ctr32_neon
ld.lld: error: undefined symbol: aws_lc_bn_mul_mont
ld.lld: error: undefined symbol: aws_lc_aes_hw_encrypt
ld.lld: error: undefined symbol: aws_lc_vpaes_encrypt
ld.lld: error: undefined symbol: aws_lc_aes_hw_set_encrypt_key
ld.lld: error: undefined symbol: aws_lc_SHA256_asm_blocks
ld.lld: error: undefined symbol: aws_lc_SHA512_asm_blocks
ld.lld: error: undefined symbol: aws_lc_aes_cbc_enc
```

同时 CMake 构建输出中会出现：
```
-- Detected generic linux platform. No assembly files will be included.
```
或
```
-- Unknown processor found. Using generic implementations
```

## 触发条件

- 构建系统: Rust/Cargo + CMake（aws-lc-sys 内部使用 cmake crate 调用 CMake 构建 aws-lc C 库）
- 阶段: linking（链接阶段，cargo build 的最终链接步骤）
- 平台: OHOS (aarch64-unknown-linux-ohos)
- 依赖: rustls (features = ["aws-lc-rs"]) → aws-lc-rs → aws-lc-sys → CMake 构建 aws-lc
- 根本触发: CMake 在 OHOS 平台上无法检测 `CMAKE_SYSTEM_PROCESSOR`（返回空字符串），
  导致 aws-lc 的 ARCH 变量被设为 "generic"，跳过所有汇编源文件（.S/.asm）的编译。
  但 C 代码中仍然通过 `extern` 引用这些汇编符号，链接时找不到实现。

## 根因分析

aws-lc 的 CMakeLists.txt 使用 `CMAKE_SYSTEM_PROCESSOR` 来检测目标处理器架构，
并根据检测结果设置 `ARCH` 变量（aarch64/x86_64/arm 等）。`ARCH` 决定：

1. 哪些汇编源文件被编译（如 `chacha-armv8.S`, `aes-armv8.S` 等）
2. Perl 脚本生成的汇编代码风格（`PERLASM_STYLE = linux64`）
3. `CRYPTO_ARCH_SOURCES` 列表

在 OHOS 平台上：
- CMake 不认识 OHOS 作为 `CMAKE_SYSTEM_NAME`（未被 CMake 内置平台列表包含）
- `CMAKE_SYSTEM_PROCESSOR` 为空（OHOS 的 /proc/cpuinfo 或 uname 输出格式与标准 Linux 不同）
- 所有 `elseif` 匹配都不命中，最终进入 `else()` 分支，`ARCH` 被设为 `"generic"`
- `if(${ARCH} STREQUAL "generic")` 触发 "No assembly files will be included" 消息
- 汇编源文件被完全排除，但 C 代码中的 `extern` 声明仍引用这些符号
- 链接器报 `undefined symbol`

## 解决方案

### 推荐方案

修补 aws-lc-sys 的两个文件：

**1. `builder/cmake_builder.rs`** — 添加 `configure_open_harmony()` 方法：

当 `target_env() == "ohos"` 时（Rust 的 aarch64-unknown-linux-ohos target 的 target_env 为 "ohos"），
调用 `configure_open_harmony()`，该方法：
- 设置 `CMAKE_SYSTEM_NAME=Linux`（让 CMake 使用 Linux 平台逻辑）
- 设置 `CMAKE_SYSTEM_PROCESSOR=aarch64`（绕过空值检测）
- 设置 `OHOS_ARCH=arm64-v8a`（供 CMakeLists.txt 的 OHOS 回退逻辑使用）
- 查找 OHOS NDK/SDK 的 CMake toolchain 文件

**2. `aws-lc/CMakeLists.txt`** — 修改 ARCH 检测逻辑：

- 在处理器检测前添加：`if(NOT CMAKE_SYSTEM_PROCESSOR) set(CMAKE_SYSTEM_PROCESSOR "aarch64") endif()`
- 在 ARCH 匹配的最终 `else()` 分支添加 OHOS 回退逻辑：检查 `OHOS_ARCH` 变量或 `CMAKE_SIZEOF_VOID_P`

补丁文件位置：`patches/0002-aws-lc-sys-cmake-arch.patch`

应用方式：在 cargo fetch 后、cargo build 前，对 cargo registry 中的 aws-lc-sys-0.41.0
目录执行 `patch -p1 -i patches/0002-aws-lc-sys-cmake-arch.patch`。

### 禁止做法

- ❌ 禁止设置 `OPENSSL_NO_ASM=1` 或 `OPENSSL_NO_ASM` CMake 选项 — 这会禁用所有汇编优化，
  虽然能消除链接错误，但会导致加密性能严重下降（10-100x），且不是根因修复
- ❌ 禁止手动在 C 代码中 stub 这些汇编符号 — 会产生不正确的加密实现
- ❌ 禁止通过 RUSTFLAGS 设置 `--cfg aws_lc_no_asm` — 同上，性能损失且非根因修复

## 验证

```bash
# 1. 应用补丁后重新编译，检查无未定义符号
cargo build --release -p codebook-lsp 2>&1 | grep -c undefined
# 预期输出: 0

# 2. 验证二进制可用
./target/release/codebook-lsp --version
# 预期输出: codebook-lsp 0.3.41

# 3. 运行测试确认加密功能正常
cargo test --release
# 预期输出: 13 passed; 0 failed
```

## 关联条目

- 相关: E001（PATH 中没有 cc 软链接 — OHOS 通用编译环境问题）
- 相关: E046（chmod 不生效 — SELinux 限制）
- 上游 issue: https://github.com/aws/aws-lc/issues (CMAKE_SYSTEM_PROCESSOR detection on non-standard platforms)
