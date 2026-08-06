# Digest-HMAC 1.05 适配笔记

## 编译环境
- 构建系统: Perl Makefile.PL (ExtUtils::MakeMaker)
- 编译日期: 2026-08-06
- 编译器: N/A (纯 Perl 模块，无编译步骤)
- 状态: published

## 编译步骤

1. 下载源码
```bash
wget https://cpan.metacpan.org/authors/id/A/AR/ARODLAND/Digest-HMAC-1.05.tar.gz
tar xzf Digest-HMAC-1.05.tar.gz
cd Digest-HMAC-1.05
```

2. 生成 Makefile
```bash
perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX
```

3. 编译（纯 Perl 模块，仅复制文件）
```bash
make
```

4. 测试
```bash
make test
# 结果: All tests successful (14 tests)
```

5. 安装到 staging
```bash
make install DESTDIR=$TEST_PREFIX
```

6. 安装到本地
```bash
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile.PL 不接受 --prefix 参数 | Perl 模块使用 INSTALL_BASE 而非 --prefix | 使用 `INSTALL_BASE=$DEFAULT_PREFIX` |
| 2 | Conan 包名必须全小写 | Conan 2.x 要求包名全小写 | conanfile.py 中 `name = "digest-hmac"` |
| 3 | test_package 找不到 Perl 模块 | Conan 未设置 PERL5LIB | `package_info()` 中通过 `runenv_info.append_path("PERL5LIB", ...)` 设置 |

## 源码修改

无修改，纯 Perl 模块直接编译通过。

## 依赖版本

- Perl 5.42.0 (系统预装)
- Digest::SHA v6.04 (Perl 5.42+ 内置)
- Digest::MD5 v2.59 (Perl 5.42+ 内置)

## 验证结果

```bash
# 测试结果
t/rfc2202.t .. ok
All tests successful.
Files=1, Tests=14,  0 wallclock secs
Result: PASS

# 模块加载测试
perl -I$DEFAULT_PREFIX/lib/perl5 -MDigest::HMAC -e 'print $Digest::HMAC::VERSION'
# 输出: 1.05

# RFC 2202 HMAC-MD5 Test Case 1
perl -e 'use Digest::HMAC_MD5; my $h=Digest::HMAC_MD5->new(chr(0x0b)x16); $h->add("Hi There"); print $h->hexdigest'
# 输出: 9294727a3638bb1c13f48ef8158bfc9d

# RFC 2202 HMAC-SHA1 Test Case 1
perl -e 'use Digest::HMAC_SHA1; my $h=Digest::HMAC_SHA1->new(chr(0x0b)x20); $h->add("Hi There"); print $h->hexdigest'
# 输出: b617318655057264e28bc0b6fb378c8ef146be00
```

## 注意事项

1. **纯 Perl 模块**: 本模块为纯 Perl 实现，无 XS 组件，编译过程简单。
2. **无外部依赖**: Digest::SHA 和 Digest::MD5 在 Perl 5.42+ 中内置，无需额外安装。
3. **Perl 路径**: Conan 配方通过 `runenv_info` 自动设置 `PERL5LIB`，消费者无需手动配置。

## 功能验证记录

**验证日期**: 2026-08-06

### 测试结果
- HMAC-MD5 RFC 2202 Test Case 1: ✅ PASS
- HMAC-SHA1 RFC 2202 Test Case 1: ✅ PASS
- 模块加载测试: ✅ PASS
- Conan L1 test_package: ✅ PASS

### 依赖发现
- Digest::HMAC_SHA1 实际使用 Digest::SHA (Perl内置) 而非 Digest::SHA1 (CPAN)
- Perl 5.42+ 已内置 Digest::SHA v6.04 和 Digest::MD5 v2.59
- 无需额外安装依赖

### 平台可用性
**完全可用** - 纯 Perl 模块，无 XS 组件，无需处理 SELinux/XS 问题
---

**编译结束**: 2026-08-06 07:10
**最终状态**: published
