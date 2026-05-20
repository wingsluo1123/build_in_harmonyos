# ShellCheck

**版本**: 0.11.0
**状态**: failed
**编译日期**: 2026-05-20

## 软件描述

ShellCheck 是一个 shell 脚本静态分析工具，由 Haskell 编写。它可以帮助发现 shell 脚本中的语法错误、语义问题和潜在的坑。

- **官方网站**: https://www.shellcheck.net/
- **GitHub**: https://github.com/koalaman/shellcheck
- **许可证**: GPL-3

## 编译状态

**当前版本 0.11.0**: 编译失败

### 失败原因

ShellCheck 是 Haskell 项目，需要 GHC (Glasgow Haskell Compiler) 和 Cabal 构建工具。

**关键障碍**:
1. **缺少 Haskell 工具链**: 系统未安装 GHC/Cabal/Stack
2. **无预编译包**: cmd-pkgs 中无 Haskell 工具预编译包（查询了 440 个包）
3. **编译依赖链过长**: 编译 GHC 需要数小时，违反 R18 预编译包优先原则
4. **官方预编译包下载失败**: GitHub releases 链接网络超时
5. **libc 兼容性问题**: 即使下载成功，Linux glibc 版本可能与鸿蒙 musl 不兼容

### 知识沉淀

- ShellCheck 是 Haskell 项目，需要 GHC/Cabal 构建工具
- cmd-pkgs 当前无 Haskell 工具链预编译包
- 编译 GHC 依赖链过长，不适合当前编译流程
- init-build 需增强对 Cabal 文件（ShellCheck.cabal）的识别

### 建议方案

1. **等待 cmd-pkgs 提供 GHC/Cabal 预编译包**
2. **使用 ShellCheck 官方预编译包**（验证 musl libc 兼容性后）
3. **考虑静态链接版本**（避免 libc 兼容性问题）
4. **使用 Docker/容器化方案**在 Linux 环境编译

## 构建信息

- **构建系统**: custom (Haskell/Cabal)
- **依赖**: GHC (required), Cabal (required)
- **编译器**: 未使用（依赖缺失）

## 参考链接

- [ShellCheck CHANGELOG](https://github.com/koalaman/shellcheck/blob/master/CHANGELOG.md)
- [Haskell Platform](https://www.haskell.org/platform/)
- [Cabal 用户指南](https://www.haskell.org/cabal/users-guide/)

---

*此文档由 openharmony-compile-agent 生成*