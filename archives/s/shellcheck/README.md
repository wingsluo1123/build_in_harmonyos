# ShellCheck

ShellCheck 是一个 shell 脚本静态分析工具，由 Haskell 编写。它可以帮助发现 shell 脚本中的语法错误、语义问题和潜在的坑。

## 功能概述

- 检测 shell 脚本中的语法错误和语义问题
- 提供详细的错误说明和修复建议
- 支持 POSIX sh、Dash、Bash 等多种 shell
- 可集成到编辑器和 CI/CD 流程中

## OHOS 适配要点

### 关键障碍

ShellCheck 是 Haskell 项目，需要 GHC (Glasgow Haskell Compiler) 和 Cabal 构建工具。

**当前状态**：
- 鸿蒙平台未预装 Haskell 工具链（GHC/Cabal/Stack）
- cmd-pkgs 中无 Haskell 工具预编译包
- 编译 GHC 依赖链过长（需数小时），违反 R18 预编译包优先原则
- 官方预编译包可能存在 libc 兼容性问题（Linux glibc vs 鸿蒙 musl）

### 建议方案

1. 等待 cmd-pkgs 提供 GHC/Cabal 预编译包
2. 使用 ShellCheck 官方预编译包（需验证 musl libc 兼容性）
3. 考虑静态链接版本（避免 libc 兼容性问题）
4. 使用 Docker/容器化方案在 Linux 环境编译

## 依赖关系

### 编译依赖
- GHC (Glasgow Haskell Compiler) - required
- Cabal (Haskell build tool) - required

### 运行依赖
- 无（静态编译版本）

## 功能验证

```bash
# 基本用法
shellcheck script.sh

# 检查多个文件
shellcheck *.sh
```

## 参考链接

- **官方网站**：https://www.shellcheck.net/
- **GitHub仓库**：https://github.com/koalaman/shellcheck
- **许可证**：GPL-3.0
- [ShellCheck CHANGELOG](https://github.com/koalaman/shellcheck/blob/master/CHANGELOG.md)
- [Haskell Platform](https://www.haskell.org/platform/)
- [Cabal 用户指南](https://www.haskell.org/cabal/users-guide/)

---

*此文档由 openharmony-compile-agent 生成*