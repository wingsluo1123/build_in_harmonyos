# retawq 0.2.6c 适配笔记

## 编译环境
- 构建系统: custom (itchconfig)
- 编译日期: 2026-08-08
- 编译器: clang
- 状态: published

## 编译步骤
```bash
conan install --requires=ncurses/6.6 --requires=openssl/1.1.1w -g PkgConfigDeps
export PKG_CONFIG_PATH=. CFLAGS="-fPIC -O2 -I<ncurses-include> -I<openssl-include>"
export LDFLAGS="-L<ncurses-lib> -L<openssl-lib>" TMPDIR=<writable-tmp>
./configure --path-prefix=$PREFIX --set-tg=curses:ncurses.h:ncursesw --set-tls=2 \
  --enable-news --enable-cookies --enable-textmodemouse --enable-ipv6 --enable-local-cgi --set-threading=1
make -j1 && make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: Permission denied | HMDFS SGID + umask 077 | umask 077→022 (patch 0001) |
| 2 | incomplete struct _win_st | ncurses 6.x opaque WINDOW | getcury()/getcurx() API (patch 0002) |
| 3 | undefined symbol RAND_egd | OpenSSL 1.1.1w OPENSSL_NO_EGD | #ifndef OPENSSL_NO_EGD (patch 0003) |
| 4 | const qualifier warning | OpenSSL 1.1.1 const return | const SSL_METHOD* (patch 0003) |

## 验证
```bash
$ retawq --version
retawq 0.2.6c - Copyright (C) 2001-2006 Arne Thomassen
```

## 依赖
- ncurses/6.6, openssl/1.1.1w, pthread (system), dl (system)
---

**编译结束**: 2026-08-09 00:11
**最终状态**: published

