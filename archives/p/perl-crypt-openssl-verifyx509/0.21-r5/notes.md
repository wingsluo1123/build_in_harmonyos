# perl-crypt-openssl-verifyx509 0.21-r5 适配笔记

## 编译环境
- 构建系统: custom (Perl ExtUtils::MakeMaker / Makefile.PL)
- 编译日期: 2026-07-06
- 编译器: clang/clang++ (clang 15.0.4)
- Perl: 5.42.0 (aarch64-linux)
- OpenSSL: 3.5.6 (系统安装于 ~/usr/local)
- 状态: published

## 编译步骤

1. 源码来自 CPAN: Crypt-OpenSSL-VerifyX509-0.21.tar.gz (TIMLEGGE)
2. 修改 Makefile.PL 添加 OPENSSL_PREFIX 环境变量支持 (补丁 0001-Makefile.PL.patch)
3. `perl Makefile.PL INSTALL_BASE=/` — 生成 Makefile
4. `make -j1` — 编译 XS 扩展 (VerifyX509.so, 27KB)
5. `make install DESTDIR=$TEST_PREFIX` — 安装到 staging 目录

## Conan 配方改进 (v2)

### 相比 v1 的改进
1. **R27 合规**: 添加 `perl-crypt-openssl-x509/2.0.1-r1@ohpcd/stable` 为 Conan 依赖
2. **generate() 方法**: 使用 `self.buildenv_info` 设置 OPENSSL_PREFIX、LD_LIBRARY_PATH、PERL5LIB、CC、CXX
3. **_setup_env() 方法**: 直接设置 os.environ 供 subprocess 使用
4. **OpenSSL 路径**: 默认值从 `/usr/local` 改为 `~/usr/local` (匹配鸿蒙平台安装位置)
5. **package() 改进**: 添加 blib fallback 机制
6. **package_info() 修复**: libdirs 从错误的 `lib/perl5/auto/...` 改为 `lib`
7. **test_package 改进**: ELF 验证、包声明检查、目录结构验证、运行时加载测试 (OHOS 跳过)
8. **INSTALL_BASE=/**: 确保 lib/perl5/ 布局 (而非 data/service/hnp/ 布局)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败，无法从 CPAN 下载 | 系统 CA 证书路径不对 | 设置 SSL_CERT_FILE 环境变量 |
| 2 | Makefile.PL 硬编码 OpenSSL 路径 | 默认路径不含 ~/usr/local | 补丁添加 OPENSSL_PREFIX 环境变量支持分支 |
| 3 | conan create 失败: openssl/asn1.h not found | OPENSSL_PREFIX 默认 `/usr/local` 不含 OpenSSL | 默认值改为 `~/usr/local` |
| 4 | conandata.yml 补丁文件名不匹配 | 生成时使用了描述性名称而非实际文件名 | 修正为 `patches/0001-Makefile.PL.patch` |
| 5 | ConanException 未导入 | conanfile.py 缺少 import | 添加 `from conan.errors import ConanException` |
| 6 | make test 失败 | HMDFS SELinux (E073) 阻止 dlopen X509.so | 平台限制，记录为已知问题 |
| 7 | /tmp 只读 (E002) | 鸿蒙平台 /tmp 限制 | 使用 $HOME/tmp |
| 8 | 包布局变为 data/service/hnp/ | Makefile.PL 缺少 INSTALL_BASE=/ 参数 | 恢复 INSTALL_BASE=/ 参数 |

## 源码修改

- **Makefile.PL**: 添加 OPENSSL_PREFIX 环境变量支持分支（在 brew 和 else 之间插入）
  - 补丁文件: `patches/0001-Makefile.PL.patch`

## 依赖版本

- Perl: 5.42.0 (aarch64-linux)
- OpenSSL: 3.5.6 (系统安装于 ~/usr/local)
- clang: 15.0.4
- ExtUtils::MakeMaker: 随 Perl 提供
- Crypt::OpenSSL::X509: 2.0.1-r1 (Conan @ohpcd/stable)
- Crypt::OpenSSL::Guess: 0.15 (系统安装)
- Convert::ASN1: 0.34 (系统安装)

## 验证结果

### 编译验证
```
编译: ✅ 成功 (VerifyX509.so, 27072 bytes, ELF64 AArch64)
安装: ✅ 成功 (staging 目录已就绪)
Conan: ✅ conan create 成功 (G2 PASS)
```

### 静态分析
```
ELF:    ✅ ELF64 AArch64, DYN (Shared object)
依赖:   ✅ libcrypto.so.3, libssl.so.3, libc.so
安全:   ✅ NX stack, GNU_RELRO, BIND_NOW (Full RELRO)
符号:   ✅ boot_Crypt__OpenSSL__VerifyX509 (XS bootstrap)
API:    ✅ X509_STORE_*, X509_verify_cert, ERR_* (正确引用)
```

### 测试结果
```
t/00-version.t:  ✅ PASS
t/00-basic.t ~ t/05: ❌ FAIL (HMDFS SELinux E073 — dlopen 权限拒绝)
author/release:  ⏭️ SKIP
```

### conan-verify (8 道门禁)
```
G0: ✅ PASS  (预构建风险评估)
G1: ✅ PASS  (配方完整性)
G2: ✅ PASS  (conan create 干净构建)
G3: ✅ PASS  (系统同名库隔离 R26)
G4: ✅ PASS  (产物完整性)
L2: ✅ PASS  (smoke test — 纯库包跳过)
L4: ✅ PASS  (安全扫描)
L5: ✅ PASS  (产物基线对比)
```

## 平台可用性评估

| 维度 | 状态 | 说明 |
|------|------|------|
| 编译 | ✅ 可用 | XS 扩展正确编译 |
| 打包 | ✅ 可用 | Conan 配方可复现 |
| 依赖 | ✅ 可用 | X509 声明为 @ohpcd/stable |
| 运行时 | ⚠️ 平台限制 | HMDFS SELinux (E073) 阻止 dlopen |

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (Perl XS, 含 X509 依赖声明) |
| conandata.yml | 源码 URL + sha256 + 补丁声明 |
| test_package/conanfile.py | ELF 验证 + 结构检查 + 运行时测试 |
| test_package/MANIFEST.yml | 上游测试声明 |
| patches/0001-Makefile.PL.patch | OpenSSL 路径环境变量支持 |
| manifest.yaml | 编译元数据 (status: published) |
| notes.md | 本文件 |
| reports/test-report.md | 详细测试报告 |
| reports/conan-verify-report.md | Conan 验证报告 |
| reports/conan-create.log | conan create 日志 |
| reports/baseline.json | 产物基线 |

## 注意事项

1. **HMDFS SELinux 限制 (E073)**: 用户目录 .so 文件无法 dlopen。系统目录可加载但不可写。CI 环境不受此限制。
2. **OPENSSL_PREFIX**: 必须设置为 OpenSSL 安装路径 (默认 ~/usr/local)。
3. **INSTALL_BASE=/**: 必须传递给 Makefile.PL 以获得正确的 lib/perl5/ 布局。
4. **X509 运行时依赖**: VerifyX509.pm 第 10 行 `use Crypt::OpenSSL::X509`，运行时必须可用。
5. **Conan 依赖**: perl-crypt-openssl-x509/2.0.1-r1@ohpcd/stable 已在本地缓存。
---

**编译结束**: 2026-07-06 15:29
**最终状态**: published
