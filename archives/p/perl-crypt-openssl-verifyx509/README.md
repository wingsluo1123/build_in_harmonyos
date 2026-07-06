# Crypt::OpenSSL::VerifyX509 (perl-crypt-openssl-verifyx509)

## 简介

Crypt::OpenSSL::VerifyX509 是一个 Perl XS 模块，提供基于 OpenSSL 的简单 X.509 证书验证功能。给定一个 CA 证书和一个待验证的证书，可以判断该证书是否由 CA 签名。

## 功能概述

- **证书验证**：验证证书是否由指定 CA 签名
- **XS 扩展**：使用 C 语言通过 Perl XS 机制实现，性能优于纯 Perl 方案
- **OpenSSL 集成**：直接调用 OpenSSL X509_STORE API 进行验证
- **应用场景**：XML 签名验证、非 SSL 环境下的证书验证

## API

| 方法 | 说明 |
|------|------|
| `new($ca_path)` | 构造函数，加载 CA 证书文件 |
| `verify($cert)` | 验证证书，成功返回 true，失败 croak |
| `DESTROY` | 析构函数，释放资源 |

## OHOS 适配要点

### 1. OpenSSL 路径

Makefile.PL 默认搜索路径不包含 OpenHarmony 用户安装路径。通过补丁添加 `OPENSSL_PREFIX` 环境变量支持分支。

### 2. INSTALL_BASE

使用 `INSTALL_BASE=/` 确保 Conan 包布局为 `lib/perl5/aarch64-linux/`。

### 3. HMDFS SELinux 限制 (E073)

OpenHarmony HMDFS 文件系统将用户目录文件 SELinux 上下文设为 `u:object_r:hmdfs:s0`，阻止 `dlopen()` 加载 .so 文件。这是平台级限制，非编译问题。CI 环境和系统目录不受此限制。

### 4. Conan 依赖

运行时依赖 `perl-crypt-openssl-x509/2.0.1-r1@ohpcd/stable` 已在 Conan 制品仓中发布。

## 依赖关系

### 编译依赖
- **OpenSSL** 3.5.6 — 系统预装 (libssl/libcrypto 头文件和库)
- **Perl** 5.42.0 — ExtUtils::MakeMaker
- **clang** 15.0.4 — C 编译器

### Conan 依赖
- **perl-crypt-openssl-x509** 2.0.1-r1 @ohpcd/stable — 运行时: Crypt::OpenSSL::X509

### 运行时依赖 (非 Conan)
- **Crypt::OpenSSL::Guess** — X509 的构建时依赖
- **Convert::ASN1** — X509 的运行时依赖

## 参考资料

- CPAN: https://metacpan.org/dist/Crypt-OpenSSL-VerifyX509
- 源码: https://cpan.metacpan.org/authors/id/T/TI/TIMLEGGE/Crypt-OpenSSL-VerifyX509-0.21.tar.gz
- 相关软件: perl-crypt-openssl-x509 (Crypt::OpenSSL::X509)
