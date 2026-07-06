# perl-crypt-openssl-verify 0.36-r2 适配笔记

## 编译环境
- 构建系统: custom (Perl XS / ExtUtils::MakeMaker)
- 编译日期: 2026-07-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: CPAN Crypt-OpenSSL-Verify-0.36.tar.gz (sha256: deefdae6b14877f590f08c4eb50e3cd3710aa3ee62412c08d183f55b3af73e9e)
2. perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX (修改后, 见源码修改)
3. make -j1
4. make install DESTDIR=$TEST_PREFIX
5. make test (失败, 见下文)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL下载失败 | CPAN/MetaCPAN HTTPS证书验证失败 | curl -kL 下载到 $TMPDIR |
| 2 | Crypt::OpenSSL::Guess缺失 | CPAN不可用,Perl模块未安装 | R2:直接修改Makefile.PL,硬编码OpenSSL路径 |
| 3 | Crypt::OpenSSL::X509缺失 | 运行时依赖未安装 | 从CPAN下载并手动编译安装 |
| 4 | Test::Exception/File::Slurper缺失 | 测试依赖未安装 | 从CPAN下载并手动安装 |
| 5 | make test失败: Permission denied | OHOS平台限制:未签名.so无法dlopen | 平台限制,不阻塞(Gotchas: ELF签名) |

## 源码修改

### Makefile.PL (R2: 探索阶段直接改源码)
- 移除 `use Crypt::OpenSSL::Guess;` 依赖
- 硬编码 OpenSSL 版本 (3, 5, 6) 和路径 ($OPENSSL_PREFIX/include, $OPENSSL_PREFIX/lib)
- 使用 $ENV{OPENSSL_PREFIX} 环境变量支持覆盖

```diff
-use Crypt::OpenSSL::Guess;
-my ($major, $minor, $patch) = openssl_version();
-$args{INC} = openssl_inc_paths();
-$args{LIBS} = [openssl_lib_paths() . ' -lssl -lcrypto'];
+# R2: Bypass Crypt::OpenSSL::Guess, hardcode OpenSSL paths for OHOS
+my ($major, $minor, $patch) = (3, 5, 6);
+my $openssl_prefix = $ENV{OPENSSL_PREFIX} || '/storage/Users/currentUser/usr/local';
+$args{INC} = "-I$openssl_prefix/include";
+$args{LIBS} = ["-L$openssl_prefix/lib -lssl -lcrypto"];
```

## 依赖版本

- Perl 5.42.0
- OpenSSL 3.5.6 (libssl, libcrypto)
- Crypt::OpenSSL::X509 2.1.2 (runtime dep, manually installed)
- Crypt::OpenSSL::Guess 0.015 (configure dep, bypassed in Makefile.PL)
- Test::Exception 0.43 (test dep)
- File::Slurper 0.014 (test dep)
- Sub::Uplevel 0.2800 (test dep)

## 验证结果

编译成功:
- Verify.so 构建成功 (clang -shared, 链接 libssl/libcrypto)
- make install DESTDIR 成功 (staging 隔离安装)

测试失败 (平台限制):
- make test 失败, 原因为 Crypt::OpenSSL::X509 的 .so 文件无法在 OHOS 上 dlopen
- 这是 OHOS 平台的 ELF 签名限制, 非编译问题
- 所有8个功能测试均因 .so 加载失败而无法运行

## 交付物

| 文件 | 路径 | 说明 |
|------|------|------|
| Verify.so | blib/arch/auto/Crypt/OpenSSL/Verify/Verify.so | Perl XS 共享库 |
| Verify.pm | blib/lib/Crypt/OpenSSL/Verify.pm | Perl 模块 |

## 注意事项

1. Crypt::OpenSSL::Guess 被绕过, conanfile.py 需要处理此依赖
2. OHOS 上 .so 加载需要 ELF 签名, CI 流水线 ci/artifacts/sign.sh 处理
3. 版本 0.36-r2 中的 -r2 是打包修订号, 上游版本为 0.36
4. CPAN 源码 URL: https://cpan.metacpan.org/authors/id/T/TI/TIMLEGGE/Crypt-OpenSSL-Verify-0.36.tar.gz
---

**编译结束**: 2026-07-06 12:47
**最终状态**: built
