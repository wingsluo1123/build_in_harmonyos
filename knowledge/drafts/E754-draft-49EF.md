# E754 — aws-lc-sys 在 OHOS/aarch64 上不产出 perlasm 汇编对象 ⇒ 链接期数百个 `aws_lc_<ver>_*` 未定义符号

> 草稿（`knowledge/drafts/E754-draft-49EF.kv`），待主编审核 `promote`。
> 来源事件：overtls 0.3.12（Rust/Cargo）适配首轮 `conan create` G2 链接失败。

## 错误特征

链接期以 `ld.lld` 报一批**只出现在 aws-lc 内部**的未定义符号，符号名统一带
`aws_lc_<x_y_z>_` 前缀，且被引用方在 `libaws_lc_sys-*.rlib` 里：

```
ld.lld: error: undefined symbol: aws_lc_0_45_0_ChaCha20_ctr32_neon
>>> referenced by chacha.c
>>>               chacha.c.obj:(aws_lc_0_45_0_CRYPTO_chacha_20) in archive .../deps/libaws_lc_sys-942402156fe1ddb3.rlib

ld.lld: error: undefined symbol: aws_lc_0_45_0_aes_hw_ctr32_encrypt_blocks
>>> referenced by bcm.c
>>>               bcm.c.obj:(aes_hw_ctr32_encrypt_blocks_wrapper) in archive .../libaws_lc_sys-....rlib

ld.lld: error: undefined symbol: aws_lc_0_45_0_bn_mul_mont
>>> referenced by bcm.c
>>>               bcm.c.obj:(aws_lc_0_45_0_BN_mod_mul_montgomery) in archive .../libaws_lc_sys-....rlib

ld.lld: error: too many errors emitted, stopping now (use --error-limit=0 to see all errors)
clang-15: error: linker command failed with exit code 1
error: could not compile `<crate>` (bin "<bin>") due to 1 previous error
```

伴生线索（aws-lc-sys 的 build script 输出里，非致命、极易被略过）：

```
cargo:warning=Building with: CMake
cargo:warning=Symbol Prefix: Some("aws_lc_0_45_0")
cargo:warning=Target platform: 'aarch64-unknown-linux-ohos'
cargo:warning=Neither OHOS_NDK_HOME nor OHOS_SDK_NATIVE are set! No toolchain found.
```

## 触发条件

- 构建系统：Cargo（Rust），且依赖图里出现 `aws-lc-rs` → `aws-lc-sys`
- 目标：`aarch64-unknown-linux-ohos`（OHOS/aarch64）；x86_64 上 perlasm/nasm 正常，**不复现**
- 阶段：`compilation`（aws-lc-sys 自身的 CMake 构建）+ `linking`（最终 `rustc` 链接）

## 根因分析

aws-lc-sys 用 CMake 构建其捆绑的 aws-lc。在 OHOS/aarch64 上：

1. CMake 探测不到 OHOS NDK（`Neither OHOS_NDK_HOME nor OHOS_SDK_NATIVE are set!`），
   即使 `CMAKE_ASM_COMPILER` 已被识别为 `/data/service/hnp/bin/clang`、ASM flags 也带了
   `--target=aarch64-unknown-linux-ohos`，**实际编译的只有 C 源**：
   `Building ASM object` 计数 = **0**；
   产物 `libaws_lc_0_45_0_crypto.a` 共 257 个成员，`llvm-ar t … | grep -iE 'armv8|neon|vpaes|aesv8'`
   **无命中**（即 0 个 aarch64 perlasm 目标）。
2. 但同一批 C 源（`bcm.c`、`chacha.c`、`e_chacha20poly1305.c`、`e_aesgcmsiv.c` …）仍按
   「有汇编」编译，其 `extern` 声明（`ChaCha20_ctr32_neon`、`aes_hw_*`、`vpaes_*`、
   `bn_add_words`、`bn_mul_mont`、`bignum_copy_row_from_table*` …）全部悬空
   ⇒ 链接期 200+ 个 `undefined symbol: aws_lc_0_45_0_*`。

**触发面容易误判**：Rust 的 Cargo feature 是**全图并集**，"上游在 `rustls`/`tokio-rustls`
写了 `default-features = false` + `features = ["ring"]`" **不能**阻止别的 crate 打开
`rustls/aws_lc_rs`。本案例的硬编码源是 `reqwest` 0.13.x：

```toml
rustls = ["__rustls-aws-lc-rs", "dep:rustls-platform-verifier", "__rustls"]
__rustls-aws-lc-rs = ["hyper-rustls?/aws-lc-rs", "tokio-rustls?/aws-lc-rs",
                      "rustls?/aws-lc-rs", "quinn?/rustls-aws-lc-rs"]
```

故「在 Cargo.toml 里 grep `aws-lc` 命中 0」**不能**证明它不在构建图里，必须反查：

```bash
cargo tree -e features -i aws-lc-rs
# └── rustls v0.23.x
#     ├── hyper-rustls v0.27.x
#     │   ├── hyper-rustls feature "aws-lc-rs"
#     │   │   └── reqwest feature "__rustls-aws-lc-rs"
#     │   │       └── reqwest feature "rustls"      ← 真凶
```

## 解决方案

### 推荐方案：把 CryptoProvider 换回 ring（改依赖 feature，不碰汇编）

对 `reqwest` 0.13.x：把 `"rustls"` 换成 **`"rustls-no-provider"`**
（= `dep:rustls-platform-verifier` + `__rustls`，不启用任何 provider），
由应用自己安装 ring 默认 provider。

改前必须确认「应用自己会安装 provider」，否则错误只是从链接期挪到**运行期**
（`no process-level CryptoProvider available`），更难查：

```bash
grep -rn 'CryptoProvider\|install_default\|default_provider' src/
```

本案例（overtls 0.3.12）已具备，故无功能损失：

- `src/lib.rs:36 ensure_rustls_crypto_provider()` → `rustls::crypto::ring::default_provider().install_default()`
- `src/tls.rs:30/46` 显式用 `rustls::crypto::ring::*` 密码套件建 `ClientConfig`（不依赖全局默认）
- 唯一的全局默认 provider 消费者是 server 侧 `reqwest::Client`（`src/panel_sync.rs:32`），
  它在 `run_server` 里紧跟 `src/server.rs:42` 的 provider 安装之后创建
- WS 握手自实现（`src/client.rs:577` 的 `tokio_tungstenite::client_async` 已注释），
  `tokio-tungstenite` 只用到 `tungstenite::{handshake,error}`，其 TLS connector 不在调用路径上

配方侧以 `conandata.yml` 的 `patches:` 段声明（`patch_type: portability`、`strip: 1`）：

```diff
--- a/Cargo.toml
+++ b/Cargo.toml
@@ -35,7 +35,7 @@
 reqwest = { version = "0.13.4", default-features = false, features = [
-    "rustls",
+    "rustls-no-provider",
     "json",
 ] }
```

### 回退方案：`AWS_LC_SYS_NO_ASM=1`

无法改依赖图时（aws-lc-rs 由多层上游硬编码、或必须用 FIPS 面），用官方开关让
aws-lc 的 CMake 给 C 源加 `-DOPENSSL_NO_ASM`，perlasm 的 `extern` 引用随之消失、
纯 C 回退实现补上同名符号：

```bash
AWS_LC_SYS_NO_ASM=1 cargo build --release
```

代价：加密性能下降；仍依赖 aws-lc 的 CMake 在 OHOS 上能跑通。
`AWS_LC_SYS_PREBUILT_NASM` 只对 x86 有效，OHOS/aarch64 无用。

### 禁止做法

- ❌ `-Wl,--unresolved-symbols=ignore-all` / `-Wl,--allow-shlib-undefined` /
  `-Wl,--warn-unresolved-symbols` / `--error-limit=0`
  —— 把链接期错误推成运行期崩溃（缺失的是 ChaCha20/Poly1305/AES/bignum 等加密原语），
  等于交付一个不可用的 TLS 栈；`--error-limit=0` 只是让同一份失败日志变长。
- ❌ 手写 stub 补 `aws_lc_0_45_0_*` 符号 —— 空实现会在握手时静默失败，属「平台限制必须降级而非绕过」。

## 验证

```bash
# ① 依赖图里确实不再有 aws-lc-rs（期望逐字：did not match any packages）
cargo tree -i aws-lc-rs
# ② 只剩 ring
cargo tree | grep -E 'aws-lc|ring'
# ③ 真机构建 + 上游测试
cargo build --release && cargo test --release --lib
```

overtls 0.3.12 实测（2026-10-06，OHOS PC aarch64）：
`cargo tree -i aws-lc-rs` → `error: package ID specification 'aws-lc-rs' did not match any packages`；
`cargo tree | grep -c aws-lc` → `0`；
`cargo build --release` rc=0；`cargo test --release --lib` → `1 passed; 0 failed`；
`conan create` 由链接失败转为 **14/14** 消费者断言全通过（含 SOCKS5 → WS 隧道 → 服务端转发 → 回显的数据面往返）。

## 关联条目

- 相关：E004（`undefined symbol` 族，但那条是 Python/ImportError 形态、处置完全不同
  —— 注意 2026-10-06 实测该条会被本错误**假命中**且 Phase B 分数为 0，勿照其方案修）
- 原则：P005（补丁须可向上游提交）、P013（平台限制必须降级而非绕过）、
  P014（环境变量与构建系统语义冲突陷阱——此处是 feature 并集语义）
