# rubyfmt 0.14.1 适配笔记

## 编译环境
- 构建系统: cargo (Rust)
- 编译日期: 2026-07-02
- 编译器: clang/clang++ (C), rustc 1.96.1 (Rust)
- 状态: built

## 编译步骤

1. 下载并解压源码: `rubyfmt-0.14.1.tar.gz`
2. 设置环境变量:
   ```bash
   export PATH="$HOME/.harmonybrew/bin:$PATH"
   export LD_LIBRARY_PATH="$HOME/.harmonybrew/lib:$LD_LIBRARY_PATH"
   export LIBCLANG_PATH="/storage/Users/currentUser/.harmonybrew/Cellar/ohos-sdk/26.0.0.18_1/native/llvm/lib"
   export CC=clang CXX=clang++
   ```
3. 修改 Cargo.toml: 为 rubyfmt 依赖添加 `default-features = false`
4. 构建: `cargo build --release --no-default-features -j1`
5. 安装: `cp target/release/rubyfmt-main $TEST_PREFIX/bin/rubyfmt`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cargo 二进制报 OpenSSL symbol not found | cargo.real 动态链接 OpenSSL 但 LD_LIBRARY_PATH 未包含 harmonybrew/lib | 设置 `LD_LIBRARY_PATH="$HOME/.harmonybrew/lib:$LD_LIBRARY_PATH"` |
| 2 | tikv-jemalloc-sys configure 失败: "OS 'ohos' not recognized" | jemalloc 内嵌的 autoconf config.sub 不识别 OHOS 平台 | 使用 `--no-default-features` 禁用 jemalloc，修改 Cargo.toml 中 rubyfmt 依赖添加 `default-features = false` |
| 3 | cargo build 报 "Text file busy" (ETXTBSY) | HMDFS 文件系统并发写入+执行冲突 | 使用 `-j1` 串行编译规避 |
| 4 | ruby-prism-sys 需要 libclang | ruby-prism crate 使用 bindgen 生成 FFI 绑定 | 设置 `LIBCLANG_PATH` 指向 ohos-sdk 的 llvm/lib 目录 |

## 源码修改

- **Cargo.toml**: 将 `rubyfmt = { path = "./librubyfmt" }` 修改为 `rubyfmt = { path = "./librubyfmt", default-features = false }`
  - 原因: 禁用 jemalloc (tikv-jemalloc-sys)，因为其内嵌 autoconf 不识别 OHOS 平台

## 依赖版本

- rustc: 1.96.1 (from ~/.harmonybrew/bin/)
- cargo: 1.96.1 (from ~/.harmonybrew/bin/)
- clang: 15.0.4 (from ohos-sdk)
- libclang.so: from ohos-sdk 26.0.0.18_1 native/llvm/lib
- OpenSSL: 3.6.3 (from ~/.harmonybrew, cargo 运行时依赖)

## 验证结果

```bash
$ rubyfmt --version
rubyfmt 0.14.1

$ echo 'def foo; 42; end' | rubyfmt
def foo
  42
end
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| rubyfmt | 55855872 bytes (53MB) | Ruby autoformatter 二进制 |

## 注意事项

- jemalloc 已禁用，使用系统默认分配器（不影响功能）
- 二进制名从 `rubyfmt-main` 重命名为 `rubyfmt`
- conanfile.py 使用自定义 build() 调用 cargo（非标准 Conan cargo 工具链）
- 构建时间约 3-4 分钟
---

**编译结束**: 2026-07-02 18:51
**最终状态**: built
