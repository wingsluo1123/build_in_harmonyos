# tcping 2.1.0 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 autotools）
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. **源码获取**: 从 GitHub mkirchner/tcping v2.1.0 tag 下载源码 tarball
2. **初始化构建**: `ohc-run.py init-build tcping 2.1.0 --url=https://github.com/mkirchner/tcping/archive/refs/tags/2.1.0.tar.gz`
3. **手动编译**: `make CC=clang CCFLAGS="-Wall -fPIC -O2"` — 编译 cli.c 和 tcping.c 生成 tcping 二进制
4. **安装测试**: 复制二进制到 test-install 目录，运行 `tcping` 验证输出正确

## 源码修改

- **Makefile**: 添加 PREFIX/DESTDIR 支持和 install 目标（补丁: 0001-Makefile.patch）
  - 添加 `all: tcping` 作为默认目标
  - 添加 `install` 目标用于 `make install DESTDIR=... PREFIX=...`
  - 将 CC/CCFLAGS 改为 `?=` 赋值，允许 Conan 传入编译器

## 依赖

- 无外部依赖（仅使用 POSIX sockets API: getaddrinfo, socket, connect, select, getsockopt, close）

## 验证结果

```
$ ./tcping
error: Usage: ./tcping [-q] [-f <4|6>] [-t timeout_sec] [-u timeout_usec] <host> <port>

$ ./tcping -t 2 127.0.0.1 80
127.0.0.1 port 80 closed.
```

## 注意事项

1. 纯 Makefile 项目，无 configure 脚本
2. tcping 是命令行工具（非库），package_type=application
3. 构建: `make CC={cc} -j1`
4. 安装: `make install DESTDIR={package_folder} PREFIX=`
---

**编译结束**: 2026-07-15 18:04
**最终状态**: published
