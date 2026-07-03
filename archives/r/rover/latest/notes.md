# rover 0.40.0 适配笔记

## 编译环境
- 构建系统: Cargo (Rust)
- 编译日期: 2026-07-03
- 编译器: clang/clang++ (Rust 1.96.1 via harmonybrew)
- 状态: published

## 源码信息
- 仓库: https://github.com/apollographql/rover
- 版本: v0.40.0
- 描述: Apollo Rover - CLI tool for working with the Apollo GraphQL Registry
- 许可证: MIT
- 语言: Rust (edition 2024)
- SHA256: 0710306b55bcc8408835040b611f337432702b17b59460a957f6d7aef640d07d

## 编译步骤

1. 下载源码: `curl -kL -o rover-v0.40.0.tar.gz https://github.com/apollographql/rover/archive/refs/tags/v0.40.0.tar.gz`
2. 解压到工作目录
3. 应用补丁: `patch -p1 < patches/0001-switch-to-ring-crypto-provider.patch`
4. 编译: `cargo build --release`
5. 安装: `cp target/release/rover $PREFIX/bin/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aws-lc-sys 链接失败: undefined symbol: aws_lc_0_41_0_ChaCha20_ctr32_neon 等 | AWS-LC cmake 构建系统在 OHOS 上 DISABLE_PERL=ON，无法生成汇编文件；ARCH 可能检测为 generic | 切换 crypto provider: reqwest 从 "rustls" 改为 "rustls-no-provider"，添加 rustls/hyper-rustls/tokio-rustls 的 ring feature |
| 2 | Go linker 失败: mapping output file failed: permission denied | OHOS tmpfs 不支持 mmap 写操作，Go 链接器无法创建输出文件 | 不使用 AWS_LC_SYS_NO_PREGENERATED_SRC (避免 Go)，改用 ring 完全绕过 aws-lc-sys |
| 3 | Savannah URL 404 | search-url 找到的 savannah/waterlan URL 已失效 | 通过 GitHub API 搜索找到 apollographql/rover 仓库 |
| 4 | SSL 证书验证失败 | OHOS 环境 HTTPS 证书问题 | 使用 curl -k 手动下载 + init-build --no-download 模式 |

## 源码修改

### patches/0001-switch-to-ring-crypto-provider.patch

修改了 5 个 Cargo.toml 文件，将 TLS crypto provider 从 aws-lc-rs 切换到 ring:

1. **Cargo.toml** (workspace root):
   - [workspace.dependencies] 添加 rustls/hyper-rustls/tokio-rustls (default-features=false, features=["ring",...])
   - [dependencies] 添加 rustls/hyper-rustls/tokio-rustls (workspace=true)
   - [dev-dependencies] reqwest features: "rustls" → "rustls-no-provider"

2. **crates/rover-client/Cargo.toml**:
   - [dependencies] reqwest features: "rustls" → "rustls-no-provider"
   - [build-dependencies] reqwest features: "rustls" → "rustls-no-provider"

3. **crates/rover-http/Cargo.toml**:
   - [dependencies] reqwest features: "rustls" → "rustls-no-provider"

4. **installers/binstall/Cargo.toml**:
   - [dependencies] reqwest features: "rustls" → "rustls-no-provider"

5. **xtask/Cargo.toml**:
   - [dependencies] reqwest features: "rustls" → "rustls-no-provider"

## 依赖版本

- Rust: 1.96.1 (harmonybrew)
- Cargo: 1.96.1
- clang: 15.0.4
- Go: 1.26.4 (harmonybrew, 用于 tree-sitter 等)
- Perl: 5.42.2

## 验证结果

```bash
$ rover --version
Rover 0.40.0

$ rover --help
Rover - Your Graph Companion
Usage: rover [OPTIONS] <COMMAND>
Commands:
  init, api-key, cloud, connector, completion, ...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/rover | 34.8 MB | ELF 64-bit aarch64 动态链接可执行文件 |

## 注意事项

- aws-lc-sys 在 OHOS 上无法构建，必须使用 ring 替代
- 所有使用 reqwest "rustls" feature 的 Cargo.toml 都必须改为 "rustls-no-provider"
- rustls 必须设置 default-features=false 并显式启用 ring feature
- ring crate 比 aws-lc-rs 更具可移植性，不依赖 C/汇编代码生成
- rust-toolchain.toml 指定 1.95.0，但系统 Rust 1.96.1 兼容（无 rustup 时忽略）
---

**编译结束**: 2026-07-03 18:49
**最终状态**: published
