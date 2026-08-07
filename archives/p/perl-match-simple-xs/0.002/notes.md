# perl-match-simple-xs 0.002 编译笔记

**编译日期**: 2026-08-07
**编译器**: Perl 5.42.0 + clang
**构建系统**: ExtUtils::MakeMaker (Makefile.PL)

---

## 编译过程

### Step 1: 源码下载

从 CPAN 下载源码包：
```
https://cpan.metacpan.org/authors/id/T/TO/TOBYINK/match-simple-XS-0.002.tar.gz
sha256: 59973e4849e46ff84484abd74f8ebf85f46fcfa8767b0183269d1907e35d1c41
```

### Step 2: 构建配置

Perl XS 模块使用 ExtUtils::MakeMaker (Makefile.PL) 构建系统：
```bash
perl Makefile.PL INSTALL_BASE=<staging_dir>
make -j1
make install
```

Makefile.PL 内部调用 ExtUtils::MakeMaker，生成标准 Makefile。
XS.xs 通过 xsubpp 转换为 XS.c，再编译为 XS.so 共享库。

### Step 3: 编译结果

编译成功，生成以下产物：
- XS.so: Perl XS 扩展模块 (aarch64-linux)
- XS.pm: Perl 模块文件

安装路径: `lib/perl5/lib/perl5/aarch64-linux/match/simple/XS.pm`
共享库: `lib/perl5/lib/perl5/aarch64-linux/auto/match/simple/XS/XS.so`

### Step 4: Conan 配方

Conan 配方 (conanfile.py) 已创建：
- 构建系统: ExtUtils::MakeMaker (custom)
- 无补丁: 源码可直接在 OHOS 上编译
- 产物: XS.so + XS.pm 复制到 package/lib/perl5/
- package_info: 通过 auto/ 目录定位 arch 目录，设置 PERL5LIB

---

## 问题与解决

### 问题 1: 模块路径嵌套

**现象**: MakeMaker 的 INSTALL_BASE 会在路径下创建 lib/perl5/ 子目录，导致 package 中出现 lib/perl5/lib/perl5/ 双层嵌套
**原因**: ExtUtils::MakeMaker 的 INSTALL_BASE 行为
**解决**: package_info() 中通过查找 auto/ 目录定位实际 arch 路径

### 问题 2: SELinux HMDFS 限制

**现象**: XS.so 从 Conan 包目录加载失败
**原因**: SELinux domain 只允许加载 hnp_file 类型文件
**解决**: 测试脚本验证 .so 和 .pm 存在，并容忍 Permission denied (E073)

---

## 知识沉淀

1. Perl XS 模块使用 ExtUtils::MakeMaker (Makefile.PL) 构建系统，非 Module::Build
2. MakeMaker INSTALL_BASE 会在路径下创建 lib/perl5/ 子目录
3. package_info() 应通过查找 auto/ 目录定位 arch 路径，而非简单 glob
4. HMDFS SELinux 限制影响所有 Perl XS 模块的运行时加载 (E073)

---

**编译结束**: 2026-08-07 10:35
**最终状态**: built（编译成功，Conan 配方已创建）
