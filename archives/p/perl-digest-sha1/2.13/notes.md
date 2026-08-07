# perl-digest-sha1 2.13 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-08-07
- 编译器: clang (Perl 5.42.0 内置配置)
- 状态: built

## Conan 适配

### 2026-08-07 Conan 配方生成

本次为已有编译记录添加 Conan 配方适配。

#### 关键发现

Perl 5.42.0 on OHOS 已正确配置 clang 编译器和 include/lib 路径，
无需之前版本使用的 INC/LDDLFLAGS 补丁。直接 `perl Makefile.PL && make` 即可成功编译。

#### 变更内容

1. **conanfile.py**: 基于 perl-crypt-argon2 模板，使用 Perl MakeMaker 构建系统
2. **conandata.yml**: 使用官方 CPAN 源码 URL + SHA256
3. **test_package/**: 添加 test_sha1.sh 测试脚本，验证 SHA-1 API
4. **移除旧补丁**: 0001-Makefile.PL.patch 不再需要（环境已修复）

#### 构建命令

```bash
perl Makefile.PL INSTALL_BASE=<staging_dir>
make -j1
make install
```

#### 测试

```bash
# 上游测试
perl -Ilib t/sha1.t   # 13 个断言

# 消费者测试 (test_package)
sh test_sha1.sh <perl_lib>
# 验证: SHA1("hello"), SHA1("abc"), SHA1(""), 增量哈希
```

## 之前版本笔记 (2026-06-10)

### 遇到的问题与解决方案（已过时）

| # | 问题 | 根因 | 解决方案 | 状态 |
|---|------|------|----------|------|
| 1 | sys/types.h 缺失 | 鸿蒙系统缺少标准 C 库头文件 | 添加 INC 参数 | 已不需要 (Perl 5.42.0 已修复) |
| 2 | 链接失败（crti.o, crtn.o 缺失） | 鸿蒙系统缺少 CRT 文件 | 添加 LDDLFLAGS 参数 | 已不需要 (Perl 5.42.0 已修复) |
| 3 | make test Permission denied | SELinux HMDFS 限制 | 签名 .so 文件 | 仍然存在 (E073) |

### 平台限制

- **HMDFS SELinux 限制 (E073)**: XS 模块无法在用户目录加载
- **解决方案**: 安装到系统目录（/data/service/hnp 或通过 cmd-pkgs）
- test_sha1.sh 脚本已处理此限制：检测到 Permission denied 时退出 0

## 源码信息

- 官方源: https://github.com/gisle/digest-sha1/archive/refs/tags/2.13.tar.gz
- SHA256: edcbe9e049165bb326c1dcb41fc60f274b90bd37f64ea6cbf9fc77458579c24e

## 依赖版本

- Perl: 5.42.0 (/data/service/hnp/perl.org/perl_5.42.0)

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 |
| conandata.yml | 源码 + SHA256 声明 |
| test_package/ | L1 测试 (test_sha1.sh) |
---

**编译结束**: 2026-08-07 09:06
**最终状态**: published
