# pandoc 3.10 适配笔记

## 编译环境
- 构建系统: Haskell/Cabal (custom)
- 编译日期: 2026-07-02
- 编译器: clang/clang++ (GHC 不可用)
- 状态: failed

## 编译步骤

1. 下载源码: `curl -L -o pandoc-3.10.tar.gz https://hackage.haskell.org/package/pandoc-3.10/pandoc-3.10.tar.gz`
2. 解压源码: `tar xzf pandoc-3.10.tar.gz`
3. 检查 GHC: `which ghc` → 未找到
4. 检查 Cabal: `which cabal` → 未找到
5. 检查 Stack: `which stack` → 未找到
6. 查询 cmd-pkgs 预编译包: 1248 个包中无 GHC/Haskell/Cabal/Stack
7. 查询 Conan 制品仓: 无 GHC/Haskell 相关包
8. 编译失败: 缺少 GHC 编译器，无法构建 Haskell 源码

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GHC 编译器不可用 | OpenHarmony 平台未提供 GHC 预编译包 | 记录为平台限制，需要先移植 GHC 到 OpenHarmony |
| 2 | Cabal 构建工具不可用 | 依赖 GHC，同上 | 同上 |
| 3 | 源码无 configure/CMakeLists.txt | pandoc 使用 Haskell/Cabal 构建系统 (pandoc.cabal) | 构建系统类型标记为 custom |
| 4 | 构建标记检测失败 | pandoc 源码无标准构建文件 (configure/Makefile/CMakeLists.txt) | 已知限制，不影响编译流程 |

## 源码信息

- 源码 URL: https://hackage.haskell.org/package/pandoc-3.10/pandoc-3.10.tar.gz
- SHA256: 9c6af03b81a6f6d4669a21635ed31888759a81b999c64856601730c2ea4ad304
- 大小: 8132KB (8327696 bytes)
- 构建文件: pandoc.cabal (Cabal 2.4 格式, build-type: Simple)
- 测试 GHC 版本: 9.6.7, 9.8.4, 9.10.3, 9.12.2

## 依赖版本

| 依赖 | 版本 | 状态 |
|------|------|------|
| GHC | 9.10.3 (推荐) | ❌ 不可用 |
| cabal-install | (随 GHC) | ❌ 不可用 |
| gmp | 6.3.0 | ✅ 系统已安装 |

## 验证结果

```bash
$ which ghc
(未找到)
$ which cabal
(未找到)
$ which stack
(未找到)
# cmd-pkgs 查询结果: 1248 个包中无 GHC/Haskell 相关包
# Conan 制品仓查询: 无 GHC/Haskell 相关包
```

## 注意事项

1. pandoc 是 Haskell 应用，必须有 GHC 才能从源码编译
2. GHC 本身是一个复杂的编译器，移植到 OpenHarmony 需要大量工作
3. 替代方案: 可考虑使用 pandoc 的预编译二进制（如果上游提供 aarch64-linux 版本）
4. pandoc 3.10 拆分了 pandoc-cli 包，命令行入口在 pandoc-cli 中
5. 运行时依赖 gmp (GNU multiple precision arithmetic library)

## 知识图谱草稿

错误模式: GHC 不可用导致 Haskell 应用编译失败
- error_signature: "ghc: command not found | cabal: command not found"
- root_cause: "OpenHarmony 平台未提供 GHC (Glasgow Haskell Compiler) 预编译包"
- rec_approach: "需要先移植 GHC 到 OpenHarmony，或使用预编译二进制"
- severity: blocker
- build_system: Haskell/Cabal
---

**编译结束**: 2026-07-02 20:54
**最终状态**: failed
