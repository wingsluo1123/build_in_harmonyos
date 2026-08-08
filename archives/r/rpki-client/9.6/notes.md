# rpki-client 9.6 Conan 适配笔记

## 编译环境
- 构建系统: autotools (configure.ac + Makefile.am)
- 编译日期: 2026-08-08
- 编译器: clang 15.0.4
- 状态: built

## 源码
- 源码 URL: https://github.com/rpki-client/rpki-client-portable/releases/download/9.6/rpki-client-9.6.tar.gz
- SHA256: 07cbd27af99f1b6096769e697e38631519c69cb642bee3af39a763fa1590d947
- 注意: GitHub auto-generated archive (refs/tags/9.6) 仅含移植层，不含 OpenBSD 源码
  必须使用 release asset (releases/download/9.6/rpki-client-9.6.tar.gz) 包含完整源码

## 编译步骤

### 1. 依赖安装 (Conan)
```bash
conan install --requires=libressl/3.9.1 --requires=musl-fts/1.2.7 \
  --requires=expat/2.8.2 --requires=zlib/1.3.1 --requires=rsync/3.3.0 \
  -r=ohpcd --build=missing
```

### 2. 构建
```bash
# autoreconf (需 automake/1.18 + libtool/2.5.4 作为 build_requires)
autoreconf -i -f

# 创建 config.guess (HarmonyOS 不被 GNU config.guess 识别)
echo '#!/bin/sh\necho "aarch64-unknown-linux-gnu"' > config.guess

# 修补 configure 的 mktemp 在 HMDFS 上失败的问题
# 将 mktemp -d "./confXXXXXX" 替换为 mktemp -d (使用 TMPDIR)

# 运行 configure
./configure --host=aarch64-unknown-linux-gnu \
  --with-tal-dir=/usr/local/etc/rpki \
  --with-base-dir=/usr/local/cache/rpki-client \
  --with-output-dir=/usr/local/db/rpki-client

# 修补 config.status 的 umask 077 在 HMDFS 上创建不可写目录的问题
# 将 umask 077 && mktemp -d 替换为 mktemp -d

# 生成 Makefile
./config.status

# 编译 (j1 因 HMDFS 不支持 mkfifo)
make -j1

# 安装
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 不含 HarmonyOS 支持 | 创建自定义 config.guess 返回 aarch64-unknown-linux-gnu |
| 2 | configure 创建临时文件失败 | HMDFS 不支持 shell 脚本在当前目录创建临时文件 | 修补 configure 将 mktemp -d "./confXXXXXX" 改为 mktemp -d |
| 3 | config.status 写入临时文件失败 | umask 077 创建的目录在 HMDFS 上不可写 | 移除 config.status 中的 umask 077 |
| 4 | make -j2 失败 | HMDFS 不支持 mkfifo (jobserver) | 使用 make -j1 |
| 5 | automake/libtool 路径问题 | Conan 包安装路径与脚本预期不一致 | 设置 PERL5LIB, ACLOCAL_PATH, _lt_pkgdatadir 环境变量 |
| 6 | GitHub archive 缺少源码 | auto-generated archive 仅含移植层文件 | 使用 release asset (含完整 OpenBSD 源码) |

## 依赖版本

| 软件 | 版本 | 说明 |
|------|------|------|
| LibreSSL | 3.9.1 | 提供 libcrypto, libssl, libtls |
| musl-fts | 1.2.7 | 文件树遍历函数 |
| expat | 2.8.2 | XML 解析 |
| zlib | 1.3.1 | 压缩库 |
| rsync | 3.3.0 | RPKI 数据同步工具 (configure 时检测) |
| automake | 1.18 | 构建工具 (build_requires) |
| libtool | 2.5.4 | 构建工具 (build_requires) |

## 验证结果

```bash
$ rpki-client -V
rpki-client-portable 9.6

$ file rpki-client
ELF shared object, 64-bit LSB arm64, dynamic
```

## 交付物

| 文件 | 说明 |
|------|------|
| sbin/rpki-client | 可执行文件 |
| share/man/man8/rpki-client.8 | man page |
| etc/rpki/*.tal | RIR Trust Anchor Locator 文件 |
| etc/rpki/*.constraints | RPKI 约束文件 |
---

**编译结束**: 2026-08-09 00:55
**最终状态**: built
