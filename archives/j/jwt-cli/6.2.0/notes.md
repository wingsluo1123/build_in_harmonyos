# jwt-cli 6.2.0 适配笔记

## 编译环境
- 构建系统: cargo (Rust)
- 编译日期: 2026-07-01
- 编译器: rustc 1.95.0 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

1. 解压源码: `tar xzf jwt-cli-6.2.0.tar.gz`
2. 进入源码目录: `cd jwt-cli-6.2.0`
3. 编译: `cargo build --release --target aarch64-unknown-linux-ohos`
4. 验证: `./target/aarch64-unknown-linux-ohos/release/jwt --version` → `jwt 6.2.0`
5. 测试: `cargo test` → 50 tests passed, 0 failed

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 无 | - | - | - |

编译过程顺利，无需额外补丁或源码修改。

## 依赖版本

Rust 依赖通过 Cargo.lock 锁定，主要依赖：
- clap 4.5.21 (CLI 参数解析)
- jsonwebtoken 9.2.0 (JWT 编解码)
- ring 0.17.7 (加密库)
- serde 1 + serde_json 1 (序列化)
- chrono 0.4.38 (时间处理)

## 验证结果

```bash
$ ./target/aarch64-unknown-linux-ohos/release/jwt --version
jwt 6.2.0

$ cargo test
test result: ok. 50 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| jwt (binary) | 33MB | JWT 编解码 CLI 工具 |

## 注意事项

- 纯二进制工具，无共享库输出，不污染系统 lib 目录
- OHOS auto-sign 会对编译产物自动签名，二进制可直接在设备上执行
- Conan 配方中 `cpp_info.libdirs` 和 `cpp_info.includedirs` 置空，因为不是库

---

**编译结束**: 2026-07-01 17:01
**最终状态**: built
