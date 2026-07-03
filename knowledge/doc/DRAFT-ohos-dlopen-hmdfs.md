# DRAFT: OHOS SELinux dlopen 策略限制 (hmdfs 标签)

> **结构化数据**: [drafts/DRAFT-ohos-dlopen-hmdfs.kv](../drafts/DRAFT-ohos-dlopen-hmdfs.kv) | **原则**: 无
> **严重度**: 🟡 medium | **分类**: selinux/runtime/shared-library | **自动修复**: ✅ install-to-system-path

---

## 错误特征

Perl XSLoader / DynaLoader 加载用户路径下的 `.so` 文件时报 `Permission denied`：

```
Can't load '/storage/Users/currentUser/.../AES.so' for module Crypt::OpenSSL::AES:
Error loading shared library .../AES.so: Permission denied
at XSLoader.pm line 94.
```

C 程序直接调用 `dlopen()` 同样失败：

```
dlopen failed: Error loading shared library .../AES.so: Permission denied
```

**关键词**: dlopen, Permission denied, shared library, .so, XSLoader, DynaLoader, hmdfs, hnp_file, SELinux

## 根因

OHOS SELinux 策略**禁止 dlopen 带有 `hmdfs` SELinux 标签的共享库文件**。仅允许 dlopen 带有 `hnp_file` 标签的文件。

| 路径 | 文件系统 | SELinux 标签 | dlopen 结果 |
|------|---------|-------------|------------|
| `/data/service/hnp/...` (系统) | hmfs | `u:object_r:hnp_file:s0` | ✅ 可加载 |
| `/storage/Users/...` (用户) | tmpfs | `u:object_r:hmdfs:s0` | ❌ Permission denied |

- `chcon` 命令不可用，无法修改文件 SELinux 标签
- 系统路径 `/data/service/hnp/` 对普通用户不可写
- 此限制与文件权限 (chmod) 无关 — 即使 `.so` 权限为 `0755` 仍被拒绝

### 与 E046 的区别

| 条目 | 问题 | 本质 |
|------|------|------|
| E046 | `chmod()` 调用不生效 | 文件系统忽略权限修改 |
| **本条目** | `dlopen()` 被 SELinux 策略拒绝 | 安全策略禁止加载特定标签的 .so |

此前部分文档将此问题误诊为 E046，实际根因为 SELinux dlopen 策略限制。

## 验证方法

```bash
# 查看 .so 文件的 SELinux 标签
ls -laZ /path/to/file.so

# 对比系统路径与用户路径的标签
ls -laZ /data/service/hnp/perl.org/.../Util.so   # hnp_file ✅
ls -laZ /storage/Users/.../AES.so                 # hmdfs ❌

# 在 Perl 中测试 dlopen
perl -e '
    require DynaLoader;
    my $handle = DynaLoader::dl_load_file("/storage/Users/.../AES.so", 0);
    if ($handle) { print "OK\n" } else { print "FAIL: " . DynaLoader::dl_error() . "\n" }
'
```

## 解决方案

### 方案 1: 安装到系统路径 (推荐，需 root)

```bash
# 将 .so 安装到系统 Perl 路径（hnp_file 标签）
cp AES.so /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Crypt/OpenSSL/AES/
chmod 755 /data/service/hnp/perl.org/.../AES.so
```

### 方案 2: 编译验证替代 (无需 root)

当无法安装到系统路径时，通过 C 程序直接调用底层 API 验证功能正确性：

```c
// 直接调用 OpenSSL AES API，使用与 CPAN 测试相同的向量
#include <openssl/aes.h>
AES_set_encrypt_key(key, 256, &enc_key);
AES_encrypt(plaintext, encrypted, &enc_key);
// 对比密文与预期值
```

### 方案 3: 修改 SELinux 策略 (系统级)

修改 OHOS SELinux 策略，允许 `hmdfs` 标签的文件被 dlopen。需要系统级策略修改权限。

## 影响范围

**平台级限制**，影响所有用户路径下的 Perl XS 模块：

| 模块 | 加载结果 |
|------|---------|
| Crypt::OpenSSL::AES | ❌ Permission denied |
| Crypt::Bcrypt | ❌ Permission denied |
| Crypt::CAST5 | ❌ Permission denied |
| DBI | ❌ Permission denied |
| DBD::Pg | ❌ Permission denied |

系统自带 XS 模块不受影响：Socket ✅、Fcntl ✅、Encode ✅、POSIX ✅、Storable ✅、List::Util ✅

## 涉及软件

perl-crypt-openssl-aes 0.21-r1（功能测试中发现，AES 加密/解密通过 C API 验证正确）。

---
*doc/DRAFT-ohos-dlopen-hmdfs.md · knowledge graph draft · 2026-07-03*
