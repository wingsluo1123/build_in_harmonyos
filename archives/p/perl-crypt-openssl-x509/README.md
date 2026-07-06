# Crypt::OpenSSL::X509

Perl 扩展模块，提供 OpenSSL X509 证书 API 的 Perl 接口，支持证书的解析、创建和操作。

## 功能概述

- 从 PEM/DER 格式加载 X509 证书
- 提取证书字段：subject、issuer、serial、version、notBefore、notAfter
- 扩展信息解析：key usage、subject alt name、basic constraints
- 证书签名算法和公钥信息提取
- CRL (Certificate Revocation List) 操作

## OHOS 适配要点

- **构建系统**: Perl ExtUtils::MakeMaker (Makefile.PL)，非 autotools/cmake
- **OpenSSL 探测**: 需设置 `OPENSSL_PREFIX` 环境变量；conanfile.py 实现了自动探测（env var → $HOME/usr/local → /usr → /data/service/hnp）
- **Conan 构建环境**: 需显式传递 `INC` 和 `LIBS` 给 `perl Makefile.PL`，确保编译器找到 OpenSSL 头文件
- **Perl 模块依赖**: Crypt::OpenSSL::Guess、Convert::ASN1、Test::Pod 需预先安装到 PERL5LIB 路径
- **运行时限制 (E073)**: HMDFS 用户目录的 SELinux 上下文 `u:object_r:hmdfs:s0` 阻止 dlopen 加载 .so 文件。软件需安装到系统目录（`/data/service/hnp/`，上下文 `u:object_r:hnp_file:s0`）才能运行时加载

## 依赖关系

### 编译依赖
- OpenSSL (libssl, libcrypto) — 系统预装
- Perl 5.x with ExtUtils::MakeMaker
- Crypt::OpenSSL::Guess (Perl 模块, configure-time)
- clang/clang++

### 运行依赖
- OpenSSL 3.x
- Perl 5.x
- Convert::ASN1 (Perl 模块)

## 参考资料

- 源码: https://github.com/dsully/perl-crypt-openssl-x509
- CPAN: https://metacpan.org/dist/Crypt-OpenSSL-X509
- OpenSSL: https://www.openssl.org/docs/
