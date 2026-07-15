# mini_httpd 1.30 适配笔记

## 编译环境
- 构建系统: makefile（简单 Makefile，无 configure）
- 编译日期: 2026-07-15
- 编译器: clang/clang++ (version 15.0.4)
- 状态: built

## 编译步骤

1. 下载源码: `curl -k -L -o ~/tmp/mini_httpd-1.30.tar.gz https://www.acme.com/software/mini_httpd/mini_httpd-1.30.tar.gz`
2. 初始化编译: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build mini_httpd 1.30 --url=file://$HOME/tmp/mini_httpd-1.30.tar.gz`
3. 修改源码适配 OpenHarmony（见下方）
4. 编译: `make -j1`
5. 安装（staging）: `make install DESTDIR=$TEST_PREFIX`
6. 验证: `mini_httpd -V`
7. 生成 Conan 配方: `python3 $SKILL_ROOT/scripts/ohc-run.py conan-init mini_httpd 1.30`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | int64_t 重定义冲突 | mini_httpd.c 定义了自己的 int64_t，与系统头文件冲突 | 添加 `#ifdef __OHOS__` 守卫，定义 `HAVE_INT64T` |
| 2 | getpass() 函数未定义 | OpenHarmony 缺少 getpass() 函数 | 扩展 MPE 的备用实现到 `#if defined(MPE) \|\| defined(__OHOS__)` |
| 3 | /tmp 目录只读 | htpasswd.c 使用硬编码 /tmp 路径 | 使用 `getenv("TMPDIR")` 动态获取临时目录 |
| 4 | Makefile 不支持 DESTDIR | BINDIR/MANDIR 硬编码为 /usr/local | 添加 PREFIX 变量和 DESTDIR 支持 |
| 5 | SSL 下载失败 | acme.com SSL 配置问题 | 使用 curl -k 跳过验证 |
| 6 | gets() 不安全 | htpasswd.c 使用废弃的 gets() | 替换为 fgets() |

## 源码修改（便携式补丁）

### 1. Makefile (0001-Makefile.patch)
- 添加 `PREFIX ?= /usr/local` 变量支持（可被 Conan 覆盖）
- 修改 BINDIR/MANDIR 使用 PREFIX
- 修改 install 目标支持 DESTDIR

### 2. htpasswd.c (0002-htpasswd.c.patch)
- 使用 `getenv("TMPDIR")` 动态获取临时目录（便携式，CI 友好）
- 扩展 getpass() 备用实现到 OpenHarmony 平台
- 使用 fgets 替代不安全的 gets

### 3. mini_httpd.c (0003-mini_httpd.c.patch)
- 添加 `#ifdef __OHOS__` 守卫定义 `HAVE_INT64T`，避免 int64_t 重定义

## 依赖版本

无外部依赖（仅使用 libcrypt 系统库）

## 验证结果

```bash
$ mini_httpd -V
mini_httpd/1.30 26Oct2018

$ ls -la sbin/
-rwxrwx--- 1 mini_httpd
-rwxrwx--- 1 htpasswd
```

## 注意事项

- mini_httpd 没有 configure 脚本，直接编辑 Makefile 配置
- 无测试套件（no make check）
- 二进制安装在 sbin 目录而非 bin 目录
- 构建产物为可执行文件（mini_httpd + htpasswd），非库文件
---

**编译结束**: 2026-07-15 23:59
**最终状态**: built
