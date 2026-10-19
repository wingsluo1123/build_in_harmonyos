# monocypher 4.0.3 适配笔记

## 编译环境
- 构建系统: makefile（无 configure，纯 Makefile）
- 编译日期: 2026-10-18
- 编译器: clang 15 (aarch64, OHOS 工具链 /data/service/hnp/bin/clang)
- 状态: built

## 编译步骤

1. 核验官方版本：GitHub tag `4.0.3`（轻量 tag）→ commit `ab2b16dd619ad5f6979a4fbe69cfa324a6fcc35f`。
2. 源码选择：官方 release tarball（`https://github.com/LoupVaillant/Monocypher/releases/download/4.0.3/monocypher-4.0.3.tar.gz`，
   sha256 `8cc9bc341a66249016db9bd70e9142d8d0aef9945973744b1ac05dbc55d8ee66`，
   与 GitHub Releases API 公布的 asset digest sha256 完全一致，经 gh-proxy 镜像下载实测核验）。
   **注意**：tag 归档（`archive/refs/tags/4.0.3.tar.gz`，sha256 `a7cbae54...`）与 release 分发物内容不同——release 含
   `tests/vectors.h`（上游测试必需）且 `src/monocypher.{c,h}` 版本字符串为 `4.0.3`；tag 归档为
   `__git__` 占位符且不含测试向量。构建与测试必须使用官方 release 分发物。（4.0.2 先例结论在 4.0.3 实测复核仍成立。）
3. `make CC=clang AR=llvm-ar RANLIB=llvm-ranlib CFLAGS='-O2 -fPIC' library`：构建
   `lib/libmonocypher.a` + `lib/libmonocypher.so.4`（含可选 ed25519 模块）→ RC=0。
4. `make check`：构建并运行上游完整测试套件（`tests/test.c` + `tests/vectors.h`）→
   **All tests OK!**（RC=0；60 个测试条目、14 个测试函数、86 处 ASSERT 系断言）。
5. 产物打包：`package()` 直接复制 `monocypher.h`、`monocypher-ed25519.h`、`libmonocypher.a`
   并生成可重定位 pkg-config 文件（上游 .pc 用 `/PREFIX` 占位符）。
6. 固化为 Conan 配方：`conanfile.py` + `conandata.yml` + `test_package/`，本机
   `conan create -pr:h=ohos-aarch64 -pr:b=ohos-aarch64` 验证通过。

## 4.0.3 相对 4.0.2 的变更（上游 CHANGELOG）

- 修复 EdDSA/Ed25519 签名的时序泄漏漏洞（timing leak）——安全更新，建议随版本跟进。
- 若干文档小修、构建系统小修、编译警告小修。
- `tests/test.c` 与 4.0.2 逐字节一致（diff 为空），测试口径完全可比；本仓 4.0.2 配方可平移。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载超时 | 网络环境限制 | conandata.yml 仅写官方原始 URL，镜像 fallback 由 CI 自动注入（规则 #13）；sha256 与官方 API digest 逐字节一致 |
| 2 | tag 归档无法跑 `make check` | tag 归档缺 `tests/vectors.h`（生成向量需 libsodium） | 使用官方 release 分发物（自带向量） |
| 3 | 上游默认 CFLAGS 含 `-march=native` | 上游 makefile 默认值，CI 不可移植 | 配方显式传 `CFLAGS='-O2 -fPIC'` |
| 4 | `/tmp` 下 `./test.out` 报 Operation not permitted | 本机 /tmp 挂载执行受限 | 测试在可执行目录（如 ~）下运行；CI worker 无此限制 |
| 5 | 上游 4.0 无 crypto_sha512 | 4.0 移除 SHA-512，主哈希为 BLAKE2b | test_package 用 crypto_blake2b 官方向量 |

## 依赖版本

- 无第三方依赖（自包含纯 C 库）。工具链：clang 15、llvm-ar、GNU Make。

## 验证结果

```bash
# 上游测试（真跑实测）
make CC=clang AR=llvm-ar RANLIB=llvm-ranlib CFLAGS='-O2 -fPIC' check
# Random seed = 12345
# Wipe / Comparisons / Encryption / Hashes / X25519 / EdDSA / Elligator /
# Curve25519 conversions 共 60 个测试条目全部通过
# All tests OK!

# Conan 消费者测试（test_package，真跑实测）
# crypto_blake2b("abc") 官方向量 + crypto_wipe 清零校验 → OK
```

## 注意事项

- 上游 license：BSD-2-Clause OR CC0-1.0（双许可），配方取 BSD-2-Clause。
- 库类型（无 CLI），不需要 commands.json（R38 不适用）。
- 非系统同名库（/lib 下无 libmonocypher），动态/静态均允许；默认 shared=False。
---

**编译结束**: 2026-10-18
**最终状态**: built
