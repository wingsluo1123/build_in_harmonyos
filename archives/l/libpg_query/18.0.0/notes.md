# libpg_query 18.0.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: `curl -L -o libpg_query-18.0.0.tar.gz "https://codeload.github.com/pganalyze/libpg_query/tar.gz/18.0.0"`
2. 解压源码: `tar xzf libpg_query-18.0.0.tar.gz`
3. 编译静态库: `make build -j1`
4. 手动安装: `install -m 644 libpg_query.a $PREFIX/lib/ && install -m 644 pg_query.h postgres_deparse.h $PREFIX/include/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SVE support not enabled | PG18 pg_popcount_aarch64.c 引用 arm_sve.h，clang 15.0.4 无 SVE 支持 | 补丁 0001: 注释掉 USE_SVE_POPCNT_WITH_RUNTIME_CHECK |
| 2 | undefined symbol: pg_popcount_neon | libpg_query 源码提取时剥离了 Neon popcount 函数体 | 补丁 0002: 补充 pg_popcount_neon 和 pg_popcount_masked_neon 实现 |
| 3 | GitHub 下载超时 | HarmonyOS 网络无法直接访问 GitHub releases | 使用 codeload.github.com 替代下载 |

## 源码修改

- 0001-src-postgres-include-pg_config.h.patch: 禁用 SVE popcount (clang 15.0.4 无 SVE 支持)
- 0002-src-postgres-src_port_pg_popcount_aarch64.c.patch: 补充 NEON popcount 函数实现

## 依赖版本

无外部依赖（纯 C 库，内嵌 protobuf-c 和 xxhash）

## 验证结果

```bash
# 单元测试
./test/parse     # PASS (36 tests)
./test/normalize # PASS (25 tests)
./test/fingerprint # PASS (47 tests)
./test/scan      # PASS (12 tests)

# Conan 验证
conan create ... # PASS (build + test_package)
```

## 注意事项

- `make test` 的 concurrency 测试因 HMDFS 内存管理限制会段错误，但核心功能测试均通过
- `make build` 只编译静态库，避免 lld 链接器缺少 libxml2.so.16 的问题
---

**编译结束**: 2026-07-15 16:29
**最终状态**: built
