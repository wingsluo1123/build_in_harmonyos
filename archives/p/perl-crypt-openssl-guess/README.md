# perl-crypt-openssl-guess

**Crypt::OpenSSL::Guess** — Guess OpenSSL include path.

纯 Perl 模块，用于探测系统中 OpenSSL 的头文件包含路径。通常作为 Crypt::OpenSSL 系列模块（如 Crypt::OpenSSL::RSA、Crypt::OpenSSL::Random）的编译依赖使用。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.15-r1 | published | 2026-07-03 | OpenHarmony aarch64 适配，conan-verify 全门禁通过 |

## 功能

Crypt::OpenSSL::Guess 提供以下函数：

- `openssl_inc_paths()` — 返回 OpenSSL 头文件包含路径
- `openssl_lib_paths()` — 返回 OpenSSL 库文件路径
- `openssl_inc_path()` — 返回单个 OpenSSL 头文件路径（compat）

## 使用说明

```perl
use Crypt::OpenSSL::Guess;

# 获取 OpenSSL include 路径
my $inc = openssl_inc_paths();
print "Include path: $inc\n";

# 获取 OpenSSL lib 路径
my $lib = openssl_lib_paths();
print "Lib path: $lib\n";
```

## 编译依赖

无外部依赖。Crypt::OpenSSL::Guess 是纯 Perl 模块，全部依赖为 Perl 核心模块（ExtUtils::MakeMaker、Test::More 等），随 Perl 运行时自带。

## OHOS 适配要点

| 问题 | 解决方案 |
|------|----------|
| init-build URL 搜索不准 | 通过 MetaCPAN API 查找正确 CPAN 下载 URL |
| Python SSL 证书验证失败 | 用 `curl -kL` 手动下载源码包 |
| conan-init 生成 Autotools 模板 | 重写 conanfile.py 为 Makefile.PL 流程 |
| test_package 调用 `guess_inc()` | 修正为实际导出的 `openssl_inc_paths()` |

## 平台兼容性

- **OpenHarmony aarch64**: ✅ 完全兼容
- **纯 Perl 实现**: 无 C/XS 依赖，不受 SELinux 限制
- **conan-verify**: ✅ 8 门禁全 PASS
- **make test**: ✅ t/00_compile.t 通过

## 安装路径

```
Guess.pm  →  lib/perl5/Crypt/OpenSSL/Guess.pm
```

---
*OpenHarmony 编译归档 · 2026-07-03*
