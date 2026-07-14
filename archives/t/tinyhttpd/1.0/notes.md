# tinyhttpd 1.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: `git clone https://github.com/EZLippi/Tinyhttpd`
2. 修改 Makefile: 将硬编码的 `gcc` 替换为 `$(CC)`，添加 `$(CFLAGS)`
3. 编译: `make CC=clang CFLAGS="-fPIC -O2 -W -Wall" -j1`
4. 安装: 手动复制 httpd 和 client 到 bin/ 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 gcc | 原始 Makefile 直接使用 gcc 命令 | conanfile.py 中用 replace_in_file 替换为 $(CC) $(CFLAGS) |
| 2 | simpleclient.c 警告: exit 未声明 | 缺少 #include <stdlib.h> | 仅警告，不影响编译 |

## 源码修改

- **Makefile**: 将 `gcc -g -W -Wall` 替换为 `$(CC) $(CFLAGS)`，支持交叉编译
  - 在 conanfile.py 的 build() 方法中通过 `replace_in_file` 完成

## 依赖版本

- 无外部依赖（仅系统 pthreads）

## 验证结果

```bash
$ file httpd
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ readelf -d httpd | grep -E "NEEDED|FLAGS"
NEEDED             Shared library: [libc.so]
FLAGS              BIND_NOW
FLAGS_1            NOW PIE

$ httpd &
httpd running on port 4000
```

## 注意事项

- httpd 硬编码监听端口 4000，无法通过命令行参数修改
- CGI 支持需要本机安装 Perl
---

**编译结束**: 2026-07-15 01:23
**最终状态**: built
