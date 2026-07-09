# yadifa

轻量级权威 DNS 服务器，支持 DNSSEC 功能。

## 功能概述

- **权威 DNS 服务**: 支持主/从区域传输（AXFR/IXFR）
- **DNSSEC**: 支持 DNS 签名、密钥轮换、NSEC/NSEC3
- **TSIG 认证**: 支持 TSIG 密钥认证的区域传输
- **动态更新**: 支持 DNS 动态更新（RFC 2136）
- **高性能**: 采用事件驱动架构，支持高并发查询
- **管理工具**: 提供 yadifa 命令行管理工具

## OHOS 适配要点

### 已知问题与解决方案

1. **平台不识别（E007）**: GNU config.guess 不包含 HarmonyOS 检测分支，需在 conanfile.py 中添加补丁
2. **pthread_setaffinity_np 不可用**: OpenHarmony 不支持 CPU 亲和性，需用 `HAS_PTHREAD_SETAFFINITY_NP` 宏守护
3. **config.status ECHO 递归**: OpenHarmony 无 ksh，config.status 中 ECHO 语法不兼容，需改为 `printf %s\n`
4. **/tmp 只读（E002）**: 编译时需设置 `TMPDIR=$HOME/tmp`
5. **autotools shebang**: cmd-pkgs 安装的 automake/libtool 需修复 shebang
6. **GitHub tarball 无 configure**: GitHub archive 不含预生成 configure 脚本，需 `autoreconf -fi`

### 与 Linux 的差异

- 不支持 `pthread_setaffinity_np`（CPU 亲和性）
- `/tmp` 目录只读，需使用 `$TMPDIR`
- 无 ksh，shell 兼容性需注意
- 动态链接器为 musl ld.so，不支持 `$ORIGIN` RPATH 扩展

## 依赖关系

### 编译依赖

- **openssl** ≥ 3.0（DNSSEC 加密、TSIG 认证）
- **zlib**（区域文件压缩）
- **autotools**（autoconf, automake, libtool — 仅 GitHub tarball 需要）

### 运行依赖

- **openssl** 3.5.6（libssl.so.3, libcrypto.so.3）
- **zlib**（libz.so）
- **musl libc**（libc.so）

## 版本

| 版本 | 状态 | 编译日期 | Conan 引用 |
|------|------|---------|------------|
| 3.0.5 | built | 2026-06-25 | yadifa/3.0.5@ohpcd/stable |

## 参考资料

- 官网: https://www.yadifa.eu
- 源码: https://github.com/yadifa/yadifa
- 文档: https://www.yadifa.eu/documentation
