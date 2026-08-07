# Crypt::OpenSSL::DSA

Perl 模块，提供 DSA（Digital Signature Algorithm）签名和验证功能。

## 简介

Crypt::OpenSSL::DSA 是 Perl 的 OpenSSL DSA 绑定模块，提供：
- DSA 密钥生成
- DSA 签名创建
- DSA 签名验证
- PEM 格式的密钥导出/导入

## 已编译版本

| 版本 | 状态 | 发布日期 |
|------|------|---------|
| 0.20 | published | 2026-08-07 |

## 安装方法

### 使用 Conan 安装

```bash
# 安装 Conan 制品仓 remote（如未配置）
conan remote add ohpcd https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/

# 安装 perl-crypt-openssl-dsa
conan install --requires=perl-crypt-openssl-dsa/0.20 -r=ohpcd

# 设置 PERL5LIB 环境变量
export PERL5LIB="$(conan cache path perl-crypt-openssl-dsa/0.20)/lib/site_perl/5.42.0:$(conan cache path perl-crypt-openssl-dsa/0.20)/lib/site_perl/5.42.0/aarch64-linux:$PERL5LIB"
```

## 依赖

- Perl 5.42.0+
- OpenSSL 1.1.1w+

## 授权协议

- Perl 模块：Artistic License 2.0 (perl_5)

## 链接

- CPAN：https://metacpan.org/pod/Crypt::OpenSSL::DSA
- GitHub：https://github.com/kmx/perl-Crypt-OpenSSL-DSA
- OpenSSL：https://www.openssl.org/
