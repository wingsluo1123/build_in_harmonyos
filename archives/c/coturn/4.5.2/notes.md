# coturn 4.5.2 适配笔记

## 编译环境
- 构建系统: custom configure + make
- 编译日期: 2026-07-02
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤
1. init-build 下载源码（GitHub 超时，使用 ghfast.top 镜像）
2. 安装预编译依赖: openssl 3.5.6, libevent 2.1.12, sqlite3 3.49.1 (均通过 cmd-pkgs)
3. ./configure --prefix=$DEFAULT_PREFIX
4. make -j2
5. make install DESTDIR=$TEST_PREFIX
6. make check (全部通过)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 写入 /tmp 失败 (Read-only) | E002: 鸿蒙 /tmp 只读 | 修改 configure 脚本使用 $TMPDIR 环境变量 |
| 2 | OpenSSL Crypto 库未找到 | 未安装 OpenSSL | 通过 cmd-pkgs 安装 openssl 3.5.6 系统包 |
| 3 | libevent 未找到 | 未安装 libevent | 安装预编译包 libevent 2.1.12 |
| 4 | undefined symbol: FIPS_mode | OpenSSL 3.x 移除了 FIPS_mode() | 添加 OPENSSL_VERSION_NUMBER < 0x30000000L 版本守卫 |

## 源码修改

1. `configure`: 修改 TMPDIR 检测逻辑，优先使用环境变量，并检查可写性
2. `src/client/ns_turn_msg.c`: 在 FIPS_mode() 调用的预处理器条件中添加 OpenSSL 3.x 版本守卫

## 依赖版本
- OpenSSL 3.5.6 (cmd-pkgs 系统包)
- libevent 2.1.12 (cmd-pkgs 系统包)
- SQLite3 3.49.1 (cmd-pkgs 系统包)

## 2026-07-08 重新编译
- 重新安装全部三个依赖为 cmd-pkgs 系统包（OpenSSL 升级到 3.5.6）
- conanfile.py requirements() 为空（所有依赖为系统包，非 Conan 包）
- generate() 方法通过 _ensure_system_deps() 自动安装缺失依赖
- Conan settings.yml 需要添加 OHOS 作为有效 OS 枚举值
- conan-verify 全部 8 道门禁通过 (G0-G4, L2/L4/L5)

## 验证结果

```
make check:
  RFC 5769 message fingerprint test(0): success
  RFC 5769 simple request short-term credentials: success
  RFC 5769 NEGATIVE fingerprint test(0): success
  RFC 5769 message structure, long-term credentials: success
  RFC 5769 message encoding: success
  RFC 5769 NEGATIVE long-term credentials: success
  RFC 5769 message fingerprint test(1): success
  RFC 5769 IPv4 response short-term credentials: success
  RFC 5769 NEGATIVE fingerprint test(1): success
  RFC 5769 IPv4 encoding: success
  RFC 5769 message fingerprint test(2): success
  RFC 5769 IPv6 response short-term credentials: success
  RFC 5769 NEGATIVE fingerprint test(2): success
  RFC 5769 IPv6 encoding: success
  oauth token A128GCM: OK
  oauth token A256GCM: OK

conan-verify: PASS (G1, G2, G3, G4, L2, L4, L5)
G0 clean build: PASS (2 patches applied, configure + make success)
```

## 注意事项
- coturn 使用自定义 configure 脚本（非 autoconf），conanfile.py 需要特殊处理
- OpenSSL 3.x 兼容性：FIPS_mode() 已在 3.x 中移除
- TMPDIR 修改是通用修复（E002），适用于所有在鸿蒙上编译的软件
- libevent 和 sqlite3 为系统包（非 Conan 包），通过 cmd-pkgs 预安装
---

**编译结束**: 2026-07-08 18:27
**最终状态**: published
