# mksh — MirBSD Korn Shell

mksh 是一个基于 Korn Shell 的现代 shell 实现，由 MirBSD 项目维护。它兼容 POSIX shell 语法，支持大量扩展功能，体积小巧，适合作为系统默认 shell 或脚本解释器使用。

## 功能概述

- 完整的 Korn Shell 语法支持（ksh88 兼容 + 部分 ksh93 扩展）
- UTF-8 多字节字符支持
- 作业控制（job control）
- 命令行编辑（Emacs 和 Vi 模式）
- 持久化命令历史
- 内置算术运算和数组
- 别名和函数定义
- 支持 `$(...)` 和 `${...}` 等现代语法

## OHOS 适配

- **构建系统**: 使用自定义 Build.sh 脚本，非标准 autotools/cmake。Build.sh 自动检测平台和编译器特性。
- **编译器**: 原生支持 clang，无需额外适配。
- **平台检测**: Build.sh 检测到 HarmonyOS 会输出"未测试"警告，但编译正常完成。
- **静态链接**: 使用 `LDFLAGS=-static` 实现静态链接（R26 终端工具规范）。
- **已知问题**:
  - HarmonyOS `/tmp` 只读，导致部分 test.sh 测试失败（非功能问题）
  - mksh 不支持 `--version`/`--help` 标志（shell 语义），Conan L2 smoke test 会失败
  - `setresuid`/`setresgid` 隐式声明警告（功能正常，函数存在于 libc）

## 依赖关系

- **编译依赖**: 无（mksh 为独立 shell 实现，无第三方库依赖）
- **运行依赖**: 仅系统 libc（静态链接后无动态依赖）

## 参考资料

- 官网: https://mbsd.evolvis.org/
- 源码: https://mbsd.evolvis.org/MirOS/dist/mir/mksh/
- Debian 包: https://snapshot.debian.org/archive/debian/20231201T000000Z/pool/main/m/mksh/
