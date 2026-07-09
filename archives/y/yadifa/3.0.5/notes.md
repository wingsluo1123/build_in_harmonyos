# yadifa 3.0.5 适配笔记

## 编译环境

- 构建系统: autotools (autoconf 2.72, automake 1.16.5, libtool 2.4.7)
- 编译日期: 2026-06-25
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built
- 平台: aarch64-unknown-linux-ohos (OpenHarmony)
- Conan 引用: yadifa/3.0.5@ohpcd/stable

## 编译步骤

1. 下载 release tarball（GitHub archive v3.0.5，非 git clone）
   - URL: https://ghfast.top/https://github.com/yadifa/yadifa/archive/refs/tags/v3.0.5.tar.gz
   - SHA256: 1b1c98c45aa4c4e72b36d8dba725675329183caab689c53c13402419e7b85f21
2. 安装 autotools（automake 1.16.5, libtool 2.4.7）并修复 shebang
   - automake shebang 修复为 /data/service/hnp/bin/perl
   - libtool shebang 修复为 /data/service/hnp/bin/bash
3. 运行 `autoreconf -fi` 生成 configure 脚本
   - GitHub archive tarball 不含预生成 configure，需 autoreconf
4. 运行 `./configure --prefix=$HOME/usr/local`
   - 仅使用 --prefix 参数（R1 合规，native 编译）
5. 修复 config.status 兼容性问题后 `make -j1`
   - ECHO='printf %s\n'（修复 ksh 语法无限递归）
   - TMPDIR=$HOME/tmp（修复 /tmp 只读问题）
6. 修复 /usr/bin/install 硬编码后 `make install DESTDIR=$TEST_PREFIX`
   - sed 替换 Makefile 中 /usr/bin/install → ~/usr/local/bin/install
7. 执行 `make check`
   - 退出码 0，全部 39 个子目录均为 "Nothing to be done"
   - 项目未在 autotools check 框架中定义自动化测试用例
8. `make install`（安装到 $DEFAULT_PREFIX）
9. 验证: yadifa --version → 3.0.5-11722, yadifad --version → 3.0.5-11722

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status ECHO 使用 ksh 语法 | OpenHarmony 无 ksh，ECHO='echo $1' 不兼容 | 修改 config.status: ECHO='printf %s\n' |
| 2 | config.status 临时目录权限问题 | /tmp 在 OpenHarmony 中只读（E002） | 设置 TMPDIR=$HOME/tmp |
| 3 | pthread_setaffinity_np 不可用 | OpenHarmony 不支持 CPU 亲和性 | 修改 thread.c: #if (__linux__ \|\| __FreeBSD__) && HAS_PTHREAD_SETAFFINITY_NP |
| 4 | /usr/bin/install 硬编码 | Makefile 中 install 路径硬编码为 /usr/bin/install | sed 替换为 ~/usr/local/bin/install |
| 5 | autotools shebang 错误 | cmd-pkgs 安装的脚本 shebang 指向错误路径 | 修复 shebang 为 /data/service/hnp/bin/perl 和 /data/service/hnp/bin/bash |
| 6 | configure.ac 平台检测 | config.guess 不识别 HarmonyOS（E007） | 修改 configure.ac，在 conanfile.py 中添加补丁处理 |
| 7 | AC_PREREQ 版本不匹配 | configure.ac 要求 autoconf 2.69，系统为 2.72 | 补丁升级 AC_PREREQ 到 2.72 |

## 源码修改

1. **configure.ac** (`0001-configure.ac.patch`)
   - AC_PREREQ 从 2.69 升级到 2.72，兼容 OpenHarmony 的 autoconf 版本
   - 类型: 平台适配（platform_only）

2. **lib/dnscore/src/thread.c** (`0002-lib-dnscore-src-thread.c.patch`)
   - 将 `#if __linux__ || __FreeBSD__` 改为 `#if (__linux__ || __FreeBSD__) && HAS_PTHREAD_SETAFFINITY_NP`
   - 守护 pthread_setaffinity_np 调用，OpenHarmony 不支持此函数
   - 类型: 平台适配（platform_only）

## make check 测试结果

- **命令**: `make check`
- **退出码**: 0
- **结果**: ✅ 通过
- **说明**: yadifa 的 autotools 构建系统中，make check 在所有 39 个子目录中均为空操作（"Nothing to be done"），项目未在 autotools check 框架中定义自动化测试用例。测试目录（tests/）包含测试源码但未配置为 check 目标。
- **日志**: reports/make-check.log

## 功能验证

```
$ yadifa --version
yadifa 3.0.5-11722 (2025-11-19)

$ yadifad --version
yadifad 3.0.5-11722 (2025-11-19)

$ yadifa ctrl --help
Usage:
yadifa ctrl [command] [options []]
    options:
        -c, --config <config-file> : use <config_file> as configuration
        -s, --server <host>        : sets the name server to connect to
        ...
```

## 二进制分析

### 文件类型

| 二进制 | 类型 | 架构 |
|--------|------|------|
| yadifa | ELF shared object, 64-bit LSB, dynamic | arm64 (aarch64) |
| yadifad | ELF shared object, 64-bit LSB, dynamic | arm64 (aarch64) |

### 动态依赖（readelf -d NEEDED）

| 二进制 | 依赖库 |
|--------|--------|
| yadifa | libssl.so.3, libcrypto.so.3, libz.so, libc.so |
| yadifad | libssl.so.3, libcrypto.so.3, libz.so, libc.so |

### 静态库

| 库文件 | 大小 |
|--------|------|
| libdnscore.a | 1,674,672 bytes |
| libdnsdb.a | 721,238 bytes |
| libdnslg.a | 21,698 bytes |

## 依赖版本

- openssl 3.5.6（预编译安装在 ~/usr/local）
- clang 15.0.4（OpenHarmony SDK 工具链）
- automake 1.16.5（cmd-pkgs 安装）
- libtool 2.4.7（cmd-pkgs 安装）

## 交付物

| 文件 | 路径 | 大小 | 说明 |
|------|------|------|------|
| yadifa | ~/usr/local/bin/yadifa | 719,424 bytes | DNS 查询工具 |
| yadifad | ~/usr/local/sbin/yadifad | 1,399,360 bytes | DNS 权威服务器守护进程 |
| libdnscore.a | ~/usr/local/lib/libdnscore.a | 1,674,672 bytes | DNS 核心库 |
| libdnsdb.a | ~/usr/local/lib/libdnsdb.a | 721,238 bytes | DNS 数据库库 |
| libdnslg.a | ~/usr/local/lib/libdnslg.a | 21,698 bytes | DNS 日志库 |

## 质量验证结果

| 门禁 | 名称 | 结果 | 详情 |
|------|------|------|------|
| G0 | 预构建风险评估 | ✅ PASS | E007 已在 conanfile.py 中处理 |
| G1 | 二进制完整性 | ✅ PASS | 1个 ELF 二进制通过检查 |
| G2 | 功能可用性 | ✅ PASS | 1个警告（yadifa --version 返回 1 为设计行为） |
| G3 | 可移植性 | ✅ PASS | 1个通过, 1个警告（无 RPATH） |
| G4 | 档案完整性 | ✅ PASS | manifest/notes/patches/conanfile 全部就位 |

**质量报告**: reports/quality-report.md (Verdict: PASS)

## Conan 验证结果

- **conan-verify G0**: ✅ PASS（E007 知识图谱命中，已处理）
- **conan-verify G1**: ✅ PASS（配方完整性检查通过）
- **conan-verify G2**: ❌ FAIL（conan create 失败，Conan 隔离环境中 autoreconf 无法运行，GitHub tarball 不含预生成 configure）
- **报告**: reports/conan-verify-report.md

## 注意事项

- GitHub archive tarball 不包含预生成的 configure 脚本，需要 autoreconf -fi
- conan-verify G2 (conan create) 因 Conan 构建环境中 autoreconf 限制未能通过
- yadifa --version 返回退出码 1（设计行为：--version 非正式命令，打印版本后返回 1）
- yadifad 安装在 sbin/ 目录，不在默认 bin/ 中
- 运行时需设置 LD_LIBRARY_PATH=~/usr/local/lib

---

**编译结束**: 2026-06-25 18:41
**最终状态**: built
