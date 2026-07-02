# E212 — Haskell 编译器 GHC 不可用导致 Haskell/Cabal 应用编译失败

## 错误特征
Conan create 失败，报错：`Package 'ghc/9.10.3@ohpcd/stable' not resolved: Unable to find 'ghc/9.10.3@ohpcd/stable' in remotes.`
或直接执行时：`ghc: command not found` / `cabal: command not found` / `runhaskell: command not found`

## 触发条件
- 构建系统: Haskell/Cabal (pandoc.cabal, build-type: Simple)
- 阶段: configuration/dependency resolution

## 根因分析
OpenHarmony 平台未提供 GHC (Glasgow Haskell Compiler) 预编译包。Haskell 应用（如 pandoc）需要 GHC 编译器才能从源码构建。cmd-pkgs（1248 个包）和 Conan 制品仓中均无 GHC。

GHC 是一个复杂的编译器，包含运行时系统（RTS）、代码生成器和大量标准库，移植到新平台需要大量工作，包括：
- GHC 源码编译（需要 bootstrap compiler）
- 平台适配（OpenHarmony 的 libc、系统调用差异）
- 运行时系统移植

## 解决方案

### 推荐方案
移植 GHC 到 OpenHarmony 平台（需要大量工作，包括 GHC 源码编译和平台适配）

### 替代方案
使用上游提供的预编译二进制（如果有 aarch64-linux 版本可用）
- 检查上游是否提供预编译二进制: `curl -sI https://github.com/jgm/pandoc/releases/download/3.10/pandoc-3.10-linux-arm64.tar.gz`

### 禁止做法
- ❌ 不要尝试用其他编译器替代 GHC（Haskell 源码只能用 GHC 编译）
- ❌ 不要使用 --build/--host/--target 交叉编译参数（本平台为 native 编译）

## 验证
```bash
which ghc && ghc --version
```

## 关联条目
- 相关: E165 (shebang 路径问题，可能在 GHC 移植后出现)
- 影响范围: 所有 Haskell/Cabal 构建的应用程序（pandoc, ShellCheck, hlint, brittany 等）
