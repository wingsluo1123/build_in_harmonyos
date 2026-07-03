# Crypt::OpenSSL::Bignum (perl-crypt-openssl-bignum)

## 简介

Crypt::OpenSSL::Bignum 是一个 Perl XS 模块，提供对 OpenSSL 大数运算 (BIGNUM) 的 Perl 接口。它允许 Perl 程序直接使用 OpenSSL 的 libcrypto 库进行高精度整数算术运算。

## 功能概述

- **大数算术**：加减乘除、模运算、幂运算等
- **数论操作**：素数生成、GCD、模逆等
- **CTX 上下文**：通过 Crypt::OpenSSL::Bignum::CTX 管理运算上下文
- **XS 扩展**：C 层直接调用 OpenSSL libcrypto，性能接近原生

## OHOS 适配要点

### 1. 构建系统

- 使用 Perl ExtUtils::MakeMaker (`perl Makefile.PL` → `make` → `make install`)
- 非标准 autotools/cmake 构建系统，conanfile.py `build_system: custom`

### 2. OpenSSL 依赖

- 依赖系统安装的 OpenSSL (libcrypto)，通过 `OPENSSL_PREFIX` 环境变量定位
- conanfile.py 的 `generate()` 方法使用 `_resolve_openssl_prefix()` 动态解析路径（pkg-config → openssl binary → 系统路径）

### 3. 平台限制

- ❌ **功能不可用**: 当前 OHOS 用户环境下模块无法加载
- **根因**: Perl 进程运行于 SELinux 上下文 `u:r:hishell_hap:s0` (受限应用沙箱)，策略禁止 dlopen `hmdfs:s0` 上下文的文件
- **影响**: `make test` 0/67 通过，模块无法 `use`
- **对照**: 系统 XS 模块 (Socket/Encode 等) 位于 `/data/service/hnp/` (`hnp_file:s0`) 可正常加载
- 不影响编译和 Conan 打包 (编译状态: published)

### 4. 解决方案

> 详细操作步骤见 `0.09-r13/reports/functional-test-report.md` §8.2

**关键发现**: 系统已有 `/usr/lib/libcrypto.so.3` (OpenSSL 3.5.6, `ext_cmd_lib:s0`, Perl 可加载)，无需额外安装 OpenSSL 依赖。只需将 Bignum.so + 2个 .pm 文件安装到系统 Perl 路径。

#### 获取编译产物

需要 3 个文件：`Bignum.so`、`Bignum.pm`、`CTX.pm`

```bash
# 方式1: 从 Conan 缓存获取 (本机构建过)
find ~/.conan2/p -path "*/perl-crypt*" -name "Bignum.so" 2>/dev/null
# .pm 文件在同目录的 lib/Crypt/OpenSSL/ 下

# 方式2: 从源码 blib 获取
BLIB=~/tmp/builds/perl-crypt-openssl-bignum-0.09-r13.work/blib
# Bignum.so → $BLIB/arch/auto/Crypt/OpenSSL/Bignum/
# Bignum.pm → $BLIB/lib/Crypt/OpenSSL/
# CTX.pm    → $BLIB/lib/Crypt/OpenSSL/Bignum/

# 方式3: 从归档配方重新构建
cd <仓库>/archives/p/perl-crypt-openssl-bignum/0.09-r13
conan create . --name=perl-crypt-openssl-bignum --version=0.09-r13 \
    -pr:b ohos-aarch64 -pr:h ohos-aarch64

# 方式4: 从 Conan 制品仓 (CI 上传后)
conan install --requires=perl-crypt-openssl-bignum/0.09-r13@ohpcd/stable
```

#### 方案 A: hdc shell 安装 (推荐 — 开发调试)

```bash
# 1. PC 上推送文件到设备
hdc file send Bignum.so /data/local/tmp/
hdc file send Bignum.pm  /data/local/tmp/
hdc file send CTX.pm     /data/local/tmp/

# 2. hdc shell 获取 root 后安装
hdc shell
su
SITE_ARCH=/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux
mkdir -p $SITE_ARCH/auto/Crypt/OpenSSL/Bignum
mkdir -p $SITE_ARCH/Crypt/OpenSSL/Bignum
cp /data/local/tmp/Bignum.so $SITE_ARCH/auto/Crypt/OpenSSL/Bignum/
cp /data/local/tmp/Bignum.pm $SITE_ARCH/Crypt/OpenSSL/
cp /data/local/tmp/CTX.pm     $SITE_ARCH/Crypt/OpenSSL/Bignum/
chmod 755 $SITE_ARCH/auto/Crypt/OpenSSL/Bignum/Bignum.so
chmod 644 $SITE_ARCH/Crypt/OpenSSL/Bignum.pm $SITE_ARCH/Crypt/OpenSSL/Bignum/CTX.pm
chcon hnp_file:s0 $SITE_ARCH/auto/Crypt/OpenSSL/Bignum/Bignum.so
chcon hnp_file:s0 $SITE_ARCH/Crypt/OpenSSL/Bignum.pm
chcon hnp_file:s0 $SITE_ARCH/Crypt/OpenSSL/Bignum/CTX.pm
exit

# 3. 验证
perl -e 'use Crypt::OpenSSL::Bignum; print "OK\n";'
# 预期输出: OK
```

**方案 D: HAP 应用打包 (推荐 — 生产部署)**

将 Bignum.so + .pm 打包进 HAP 应用，通过应用安装机制部署到正确 SELinux 上下文路径。详见测试报告 §8.2 方案 D。

## 依赖关系

### 编译依赖
- **OpenSSL** (libcrypto) — 必需，系统级依赖
- **Perl** (≥ 5.42.0) — 必需，构建工具链

### 运行依赖
- libcrypto.so — 运行时库依赖

## 参考资料

- CPAN：https://metacpan.org/dist/Crypt-OpenSSL-Bignum
- 源码：https://cpan.metacpan.org/authors/id/K/KM/KMX/Crypt-OpenSSL-Bignum-0.09.tar.gz
- 相关软件：OpenSSL, Perl
