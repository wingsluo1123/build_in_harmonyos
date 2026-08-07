# perl-crypt-openssl-dsa 0.20 适配笔记

## 编译环境
- 构建系统: ExtUtils::MakeMaker (Perl)
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: published (Conan adapted)

## 编译步骤

1. 安装 OpenSSL 依赖:
   ```bash
   curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- openssl 1.1.1w
   ```

2. 生成 Makefile:
   ```bash
   export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
   perl Makefile.PL LIBS="-L$HOME/usr/local/lib -lcrypto" INC="-I$HOME/usr/local/include"
   ```

3. 编译:
   ```bash
   make -j1
   ```

4. 验证产物:
   ```bash
   file blib/arch/auto/Crypt/OpenSSL/DSA/DSA.so  # ELF shared object
   readelf -d blib/arch/auto/Crypt/OpenSSL/DSA/DSA.so | grep NEEDED  # libcrypto.so.1.1
   readelf -s blib/arch/auto/Crypt/OpenSSL/DSA/DSA.so | grep boot_Crypt  # XS boot function
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile.PL 需要指定 OpenSSL 路径 | 无 pkg-config，需显式指定 | 使用 LIBS 和 INC 参数 |
| 2 | char/unsigned char 指针类型警告 | DSA.xs 中 Perl SvPV 返回 char* | 仅警告，不影响功能 |

## 与 Crypt::OpenSSL::RSA 的区别

1. **无 Crypt::OpenSSL::Guess 依赖**: DSA 的 Makefile.PL 自带 OpenSSL 检测逻辑（OPENSSL_PREFIX env var）
2. **仅依赖 libcrypto**: DSA 只需要 `-lcrypto`，不需要 `-lssl`
3. **无需 LDDLFLAGS 补丁**: 默认链接器标志在 OHOS 上正常工作

## 源码修改

无补丁。编译成功，仅有类型转换警告（char* vs unsigned char*），不影响功能。

## 依赖版本

- Perl: 5.42.0
- OpenSSL: 1.1.1w (路径 ~/usr/local，通过 cmd-pkgs 安装)
- 编译工具: clang, make

## Conan 适配

### conanfile.py 特性
- `source()`: 从 CPAN 下载源码 (conandata.yml)
- `build()`: 检测 OpenSSL 路径 → perl Makefile PL → make
- `package()`: 从 blib/ 目录复制 .so 和 .pm 文件
- `package_info()`: 设置 PERL5LIB 环境变量供消费者使用
- R32: `settings.os` 检查 `in ("Linux", "OHOS")`
- R33: 所有路径运行时检测，无硬编码绝对路径

### test_package 特性
- 静态分析验证: perl -c (语法), readelf (ELF/符号/依赖)
- 不依赖运行时加载（OHOS SELinux 可能阻止 .so 加载）

## 验证结果

```bash
# 编译产物检查
find blib -type f \( -name "*.pm" -o -name "*.so" \)
# 输出:
# blib/lib/Crypt/OpenSSL/DSA.pm
# blib/arch/auto/Crypt/OpenSSL/DSA/DSA.so

# ELF 验证
file blib/arch/auto/Crypt/OpenSSL/DSA/DSA.so
# ELF shared object, 64-bit LSB arm64

# OpenSSL 依赖验证
readelf -d blib/arch/auto/Crypt/OpenSSL/DSA/DSA.so | grep NEEDED
# libcrypto.so.1.1, libc.so

# XS boot 函数验证
readelf -s blib/arch/auto/Crypt/OpenSSL/DSA/DSA.so | grep boot_Crypt
# boot_Crypt__OpenSSL__DSA
```

---
**编译结束**: 2026-08-07
**最终状态**: published (Conan recipe created and verified)
