# qpage 3.3 适配笔记

## 编译环境
- 构建系统: 自带 autoconf-2.12 生成的 `configure` + 手写 `Makefile`
- 编译日期: 2026-10-15
- 编译器: OHOS SDK clang（`tools.build:compiler_executables`）
- 状态: built

## 编译步骤

1. `source()`：从 NetBSD pkgsrc distfiles 镜像取上游 `qpage-3.3.tar.Z`（HTTPS，
   sha256 已固定），用内置的纯 Python `unlzw()` 解压 legacy `compress(1)` LZW 容器，
   再展开 tar 并去掉顶层目录。
2. `build()`：`CC=<clang> CFLAGS="-Wall -O2" sh ./configure --prefix=<pkg>`，随后
   `make CC=<clang> CFLAGS="-Wall -O2" -j1`，产出 `qpage`。
3. `package()`：安装 `bin/qpage`、`share/man/man1/qpage.1`、
   `etc/qpage.conf.sample`（`example.cf`）与许可证。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游只有明文 HTTP 的 `qpage.org`/`tomiii.com`，且产物是 `.tar.Z` | 仓库规则禁止明文 `http://`；`qpage.org` 的 https 会超时/重定向 | 改用 NetBSD pkgsrc distfiles 镜像 `ftp.jaist.ac.jp`（HTTPS，字节一致，sha256 与 FreeBSD distinfo 一致） |
| 2 | Conan `get()/unzip()` 不认识 `.Z` | `unzip()` 只处理 tar.gz/tgz/tbz2/tar.bz2/tar/gz/tar.xz/txz，否则退回 `zipfile`；Python `tarfile` 也不支持 LZW `.Z` | `source()` 用 `download()` 取回 `.Z`，再用内置纯 Python `unlzw()` 解码（compress 格式在码宽切换/CLEAR 时按 8 位边界对齐） |
| 3 | 客户端固定连 SNPP 端口 444 | 端口由 `getservbyname("snpp","tcp")` 或编译常量 444 决定，命令行不可指定；OHOS 非特权进程不能 bind <1024 | 消费者测试编译一个 LD_PRELOAD shim 拦截 `connect()`，把目标 444 改写为高位端口，在本地跑 mock SNPP 服务器做真实协议往返（不改上游） |

## 依赖版本

无三方依赖（仅 libc）。

## 验证结果

```bash
# 上游测试：无（N=0，Makefile 无 check/ctest，无 tests/）
# 消费者（test_package/test_qpage.sh）
QPAGE_CHECK_SUMMARY checks=29 fails=0
```

## 注意事项

- `qpage` 同时含客户端与服务器（daemon）代码；默认 `make` 产出完整二进制。
  服务器模式需要 root、配置文件与 `/var/spool` 队列目录，非特权环境仅验证客户端路径。
- SNPP 交互序列（客户端侧）：`220` 问候 → `CALLerid` → `PAGEr`（可带
  `HOLDuntil`/`COVErage`/`LEVEl`）→ `DATA` → 消息体 → `.` → `SEND` → `QUIT`。
