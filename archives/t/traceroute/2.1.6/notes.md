# traceroute 2.1.6 适配笔记

## 编译环境
- 构建系统: makefile (custom, not autoconf/cmake)
- 编译日期: 2026-07-16
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 下载源码：`curl -L -o ~/tmp/traceroute-2.1.6.tar.gz "https://sourceforge.net/projects/traceroute/files/traceroute/traceroute-2.1.6/traceroute-2.1.6.tar.gz/download"`
2. 初始化：`ohc-run.py init-build traceroute 2.1.6 --url=...`
3. 编译：`make env=yes CC=clang prefix=$DEFAULT_PREFIX`
4. 安装到 staging：`make env=yes prefix=$DEFAULT_PREFIX install DESTDIR=$TEST_PREFIX`
5. 验证：`traceroute --version`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make: No rule to make target '-lm'` | `LIBDEPS = $(filter-out -L%,$(LIBS))` 只过滤 `-L%`，未过滤 `-l%`，导致 `-lm` 被当作文件依赖 | 修改为 `LIBDEPS = $(filter-out -L% -l%,$(LIBS))` |
| 2 | 默认 CC=gcc 在 OHOS 上不可用 | Make.rules 默认使用 gcc，OHOS 平台只有 clang | 修改默认 CC 为 clang |

## 源码修改

### Make.rules
1. **LIBDEPS 修复**: 过滤 `-l%` 选项，避免 `-lm` 被当作文件依赖
   ```diff
   -LIBDEPS = $(filter-out -L%,$(LIBS))
   +LIBDEPS = $(filter-out -L% -l%,$(LIBS))
   ```
2. **CC 默认值修复**: 将默认编译器从 gcc 改为 clang
   ```diff
   -$(call set, CC, $$(CROSS)gcc)
   +$(call set, CC, $$(CROSS)clang)
   ```

## 依赖版本

- 无外部依赖，仅需标准 C 库 (libc.so) 和数学库 (-lm)

## 验证结果

```bash
$ traceroute --version
Modern traceroute for Linux, version 2.1.6
Copyright (c) 2016  Dmitry Butskoy,   License: GPL v2 or any later
```

## 产物

| 文件 | 说明 |
|------|------|
| traceroute | 可执行文件 (ELF 64-bit, PIE, dynamic) |
| libsupp.a | 支持库 (静态) |
| clif.h | CLI 解析库头文件 |
| traceroute.8 | man 手册页 |

## 注意事项

1. **权限需求**：traceroute 需要 raw socket 权限发送 UDP/ICMP 包。
2. **UDP 模式**：默认使用 UDP 协议，功能等同于 udptraceroute。
3. **功能完整**：支持 UDP、ICMP、TCP、DCCP 等多种探测模式。
4. **安全特性**：PIE + BIND_NOW + RELRO，符合安全要求。
---

**编译结束**: 2026-07-16 01:19
**最终状态**: built
