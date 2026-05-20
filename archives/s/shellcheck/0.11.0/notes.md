# shellcheck 0.11.0 适配笔记

## 编译环境
- 构建系统: custom (Haskell/Cabal)
- 编译日期: 2026-05-20
- 编译器: 未使用（依赖缺失）
- 状态: failed

## 编译步骤

ShellCheck 是 Haskell 项目，标准编译流程为：
1. 安装 GHC (Glasgow Haskell Compiler)
2. 安装 Cabal 或 Stack 构建工具
3. 解压源码到工作目录
4. 使用 Cabal 构建：`cabal build`
5. 安装到目标目录：`cabal install --prefix=$DEFAULT_PREFIX`

**实际情况**：
- 步骤 1-2 无法完成：系统缺少 GHC/Cabal，cmd-pkgs 无预编译包
- 官方预编译二进制包下载失败（网络超时）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺少 Haskell 构建工具 | 系统未预装 GHC/Cabal | 查询 cmd-pkgs：无 Haskell 工具预编译包（440个包中无ghc/cabal/haskell） |
| 2 | 编译 GHC 依赖链过长 | GHC 需要 GMP/LLVM 等复杂依赖，编译需数小时 | 根据R18原则，避免编译链过长，放弃编译 |
| 3 | 官方预编译包下载失败 | GitHub releases 链接网络超时 | wget/curl 均超时，无法获取 |
| 4 | 预编译包可能不兼容 | Linux glibc 版本 vs 鸿蒙 musl libc | 即使下载成功，可能存在 libc 兼容性问题 |

**最终决策**：
- 根据 SKILL.md R18（预编译包优先原则），编译 GHC 依赖链过长，不符合"避免浪费时间"原则
- 标记为 failed，等待以下情况之一解决：
  1. cmd-pkgs 提供 GHC/Cabal 预编译包
  2. 网络恢复后可下载 ShellCheck 官方预编译包
  3. 验证 glibc 版本在鸿蒙上的兼容性

## 源码修改

无补丁。源码未修改。

## 依赖版本

**缺失的关键依赖**：
- GHC: 未安装（cmd-pkgs 无预编译包）
- Cabal: 未安装（cmd-pkgs 无预编译包）
- Stack: 未安装（cmd-pkgs 无预编译包）

**ShellCheck 源码依赖（ShellCheck.cabal）**：
- aeson >= 1.4.0 && < 2.3
- array >= 0.5.1 && < 0.6
- base >= 4.8.0.0 && < 5
- bytestring >= 0.10.6 && < 0.13
- containers >= 0.5.6 && < 0.9
- deepseq >= 1.4.1 && < 1.6
- Diff >= 0.4.0 && < 1.1
- fgl >= 5.7.0 || >= 5.8.1.1
- filepath >= 1.4.0 && < 1.6
- mtl >= 2.2.2 && < 2.4
- parsec >= 3.1.14 && < 3.2
- QuickCheck >= 2.14.2 && < 2.17
- regex-tdfa >= 1.2.0 && < 1.4
- transformers >= 0.4.2 && < 0.7
- directory >= 1.2.3 && < 1.4
- process

## 验证结果

```bash
# 检查 Haskell 工具
which ghc cabal stack
# 输出：ghc not found, cabal not found, stack not found

# 查询预编译包
python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps --list-available
# 结果：440个包，无ghc/cabal/haskell相关包

# 下载官方预编译包
wget https://github.com/koalaman/shellcheck/releases/download/v0.11.0/shellcheck-v0.11.0.linux.aarch64.tar.xz
# 错误：wget: connect: Operation timed out
```

## 交付物

无交付物。编译失败，无二进制产物。

## 注意事项

### ShellCheck 项目特点
1. **Haskell 项目**：不是标准的 autotools/CMake 项目
2. **构建工具**：需要 GHC + Cabal/Stack
3. **依赖复杂**：有 15+ 个 Haskell 库依赖
4. **官方提供预编译**：但需要验证 musl libc 兼容性

### 鸿蒙平台适配难点
1. **Haskell 工具链缺失**：需要编译 GHC（时间成本过高）
2. **libc 兼容性**：glibc 预编译包可能在 musl 上不兼容
3. **建议方案**：
   - 优先等待 cmd-pkgs 提供 Haskell 工具链预编译包
   - 或验证 ShellCheck 预编译包的 musl 兼容性（静态链接版本）
   - 考虑使用 Docker/容器化方案在 Linux 环境编译

### R18 适用性分析
根据 SKILL.md R18（预编译包优先原则）：
- ❌ cmd-pkgs 无 GHC/Cabal 预编译包
- ❌ 官方预编译包下载失败
- ❌ 编译 GHC 依赖链过长（数小时）
- ✅ 正确决策：标记为 failed，避免无效时间投入

## 知识提取

### 发现的平台真理（L1）
- **Haskell 工具链缺失**：鸿蒙平台未预装 GHC/Cabal/Stack
- **cmd-pkgs 覆盖范围**：当前 440 个预编译包中无 Haskell 生态
- **构建系统识别**：init-build 需增强对 Haskell/Cabal 项目的识别（当前误判为 autotools）

### 建议的改进
1. software-registry.yaml 应标记 shellcheck 为 `build_system: custom` (Haskell)
2. 提示用户：Haskell 项目需要额外工具链，不适合当前编译流程
3. 增强 pre-scan：检测 Cabal 文件（ShellCheck.cabal）时，提前报错"需要 GHC"
**失败原因**: 缺少 Haskell 构建工具（GHC/Cabal），无预编译包，依赖链过长不符合 R18 原则
---

**编译结束**: 2026-05-20 15:51
**最终状态**: failed
