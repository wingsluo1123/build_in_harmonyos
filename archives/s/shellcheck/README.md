# ShellCheck

## 简介

ShellCheck 是一个 shell 脚本静态分析工具，由 Haskell 编写。它可以帮助发现 shell 脚本中的语法错误、语义问题和潜在的坑。

## OHOS 适配

### 主要障碍

ShellCheck 是 Haskell 项目，需要 GHC (Glasgow Haskell Compiler) 和 Cabal 构建工具。

**关键适配要点**：
1. **缺少 Haskell 工具链**: 鸿蒙平台未预装 GHC/Cabal/Stack
2. **无预编译包**: cmd-pkgs 中无 Haskell 工具预编译包
3. **编译依赖链过长**: 编译 GHC 需要数小时，违反 R18 预编译包优先原则
4. **libc 兼容性**: Linux glibc 预编译版本可能与鸿蒙 musl 不兼容

### 建议方案

1. **等待 cmd-pkgs 提供 GHC/Cabal 预编译包**
2. **使用 ShellCheck 官方预编译包**（验证 musl libc 兼容性后）
3. **使用静态链接版本**（避免 libc 兼容性问题）
4. **使用 Docker/容器化方案**在 Linux 环境编译

## 依赖

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

## 参考

- **官方网站**: https://www.shellcheck.net/
- **GitHub**: https://github.com/koalaman/shellcheck
- **许可证**: GPL-3.0
- [ShellCheck CHANGELOG](https://github.com/koalaman/shellcheck/blob/master/CHANGELOG.md)
- [Haskell Platform](https://www.haskell.org/platform/)
- [Cabal 用户指南](https://www.haskell.org/cabal/users-guide/)