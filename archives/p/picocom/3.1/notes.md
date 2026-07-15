# picocom 3.1 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile 项目，无 configure）
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

picocom 是纯 Makefile 项目，无 configure 脚本，也无 install 目标。

1. `make CC=clang CFLAGS="-Wall -g -fPIC -O2" LDFLAGS="-g" -j1`
2. 手动安装: `cp picocom $TEST_PREFIX$DEFAULT_PREFIX/bin/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 install target | Makefile 没有 install 目标 | 手动 `cp picocom` 到 staging 和安装目录 |
| 2 | conan-init 生成 autotools 模板 | init-build 默认检测为 autotools | 手动重写 conanfile.py 为 makefile 类型 |

## 源码修改

无源码修改。picocom 3.1 在 OpenHarmony 上原生编译成功，无需补丁。

## 依赖版本

无外部依赖。picocom 仅依赖系统 libc 和 termios。

## 验证结果

```bash
$ picocom --help
picocom v3.1

Compiled-in options:
  TTY_Q_SZ is 0
  HIGH_BAUD is enabled
  USE_FLOCK is enabled
  LINENOISE is enabled
  HISTFILE is: .picocom_history

Usage is: picocom [options] <tty port device>
...
```

## 注意事项

- picocom 没有标准 install target，需要手动复制二进制
- picocom 3.1 版本来源为官方 GitHub npat-efault/picocom
- picocom 无测试套件，跳过 make check
- picocom 包含内嵌 linenoise 库 (linenoise-1.0/)
---

**编译结束**: 2026-07-15 20:02
**最终状态**: built
