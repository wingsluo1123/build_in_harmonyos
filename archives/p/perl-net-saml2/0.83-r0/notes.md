# perl-net-saml2 0.83-r0 适配笔记

## 编译环境
- 构建系统: perl Makefile.PL (ExtUtils::MakeMaker)
- 编译日期: 2026-06-26
- 编译器: clang/clang++ (纯 Perl 模块，无 C 编译)
- Perl 版本: 5.42.0 (aarch64-linux)
- 状态: built (conan-verify PASS)

## 编译步骤

1. 从 CPAN 下载 Net-SAML2-0.83.tar.gz
2. 解压源码: `tar xzf Net-SAML2-0.83.tar.gz`
3. 生成 Makefile: `perl Makefile.PL`
4. 编译: `make`
5. 安装到 staging: `make install DESTDIR=$TEST_PREFIX`
6. 验证: 22 个 .pm 文件正确生成在 blib/lib/ 目录下
7. Conan 配方生成与验证: `ohc-run.py conan-init` + `ohc-run.py conan-verify` 全部通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 模块无法加载 | Net::SAML2 依赖 9 个 XS 模块 (Crypt::OpenSSL::*, XML::LibXML, XML::Sig 等)，这些模块包含 .so 文件 | 需编译安装 XS 依赖模块，详见功能测试报告 |
| 2 | XS 模块 .so 无法加载 | SELinux HMDFS 限制：`hishell_hap` 域只能加载 `hnp_file:s0` 类型的文件，HMDFS 上的 .so 文件 context 为 `hmdfs:s0` | 需通过 HNP 包安装到 `/data/service/hnp/` 系统目录，与 perl-dbd-pg 情况相同 |
| 3 | conanfile.py deprecated 警告 | 使用了 Conan 1.x 的 `env_info`，在 Conan 2.x 中已废弃 | 改用 `runenv_info.prepend_path()` 替代 `env_info` |
| 4 | LWP::Protocol::https 无法加载 | 依赖 Net::SSLeay (.so)，受 SELinux 限制 | 需 HNP 安装 Net::SSLeay |
| 5 | CPAN 下载工具不可用 | cpan 命令依赖 LWP::Simple，而 LWP 依赖 Net::SSLeay (XS)，形成循环依赖 | 手动用 curl 从 cpan.metacpan.org 下载模块源码 |

## 源码修改

无补丁。Net::SAML2 0.83 为纯 Perl 模块，源码无需修改即可在鸿蒙平台编译。

## 依赖版本

### 已安装的纯 Perl 依赖 (29/38)
- Carp (core v1.54), Exporter (core v5.79), Digest::MD5 (core v2.59)
- List::Util (core v1.6801), MIME::Base64 (core v3.16_01)
- IO::Compress::RawDeflate (core v2.213), IO::Uncompress::RawInflate (core v2.213)
- DateTime (v1.66), DateTime::Format::XSD (v0.4), DateTime::HiRes (v0.04)
- Moose (v2.4000), Moose::Role (v2.4000), MooseX::Types (v0.51)
- MooseX::Types::Common::String (v0.001015), MooseX::Types::DateTime (v0.13)
- MooseX::Types::Moose (v0.51), MooseX::Types::URI (v0.10)
- Try::Tiny (v0.31), Types::Serialiser (v1.01), namespace::autoclean (v0.31)
- URI (v5.21), URI::Encode (v1.1.1), URI::Escape (v5.21), URI::QueryParam (v5.21)
- URN::OASIS::SAML2 (v0.007), XML::Generator (v1.13)
- File::Slurper (v0.014), HTTP::Request::Common (v6.46), LWP::UserAgent (v6.81)

### 缺失的 XS 依赖 (9/38)
- Crypt::OpenSSL::Random (XS, .so 已编译但 SELinux 限制)
- Crypt::OpenSSL::Verify (XS, 需 OpenSSL 头文件)
- Crypt::OpenSSL::X509 (XS, 需 OpenSSL 头文件)
- Crypt::PK::RSA (XS, CryptX 包)
- LWP::Protocol::https (依赖 Net::SSLeay XS)
- XML::Enc (XS, 依赖 XML::LibXML)
- XML::LibXML (XS, 需 libxml2 + Alien::Base)
- XML::LibXML::XPathContext (XS, XML::LibXML 子模块)
- XML::Sig (XS, 依赖 Crypt::OpenSSL::* 和 XML::LibXML)

### 系统可用的编译依赖
- OpenSSL 1.1.1w: 头文件 `/storage/Users/currentUser/usr/local/include/openssl/`，库 `/storage/Users/currentUser/usr/local/lib/libssl.so.1.1`
- libxml2 2.15.3: 头文件 `/storage/Users/currentUser/usr/local/include/libxml2/`，库 `/storage/Users/currentUser/usr/local/lib/libxml2.so`
- clang 18.1.8

## 验证结果

```bash
# Conan 验证 (全部通过)
$ python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify perl-net-saml2 0.83-r0
G0: ✅ PASS  G1: ✅ PASS  G2: ✅ PASS  G3: ✅ PASS  G4: ✅ PASS
L2: ✅ PASS  L4: ✅ PASS  L5: ✅ PASS

# 产物完整性 (22 个 .pm 文件)
$ find lib/ -name "*.pm" | wc -l
22

# 模块加载测试 (失败，因 XS 依赖缺失)
$ perl -I lib/ -MNet::SAML2 -e 'print $Net::SAML2::VERSION'
# 失败: Can't locate Crypt/OpenSSL/Verify.pm (XS 依赖)
```

## 注意事项

1. **SELinux HMDFS 限制**: XS 模块的 .so 文件无法从用户目录 (`~/usr/local/lib/`) 加载，需通过 HNP 包安装到系统目录 (`/data/service/hnp/`)
2. **循环依赖问题**: CPAN 工具依赖 LWP，LWP 依赖 Net::SSLeay (XS)，形成循环。需手动下载模块源码
3. **Alien::Base 依赖**: XML::LibXML 2.x 依赖 Alien::Base::Wrapper，增加了编译复杂度
4. **纯 Perl 模块可用**: Net::SAML2 本身为纯 Perl，编译无问题。运行时功能受 XS 依赖限制

---

**编译结束**: 2026-06-26 18:08
**功能测试**: 2026-06-30
**最终状态**: published (conan-verify 全部通过 G0-G4 + L5, 功能测试详见 reports/test-report.md)
