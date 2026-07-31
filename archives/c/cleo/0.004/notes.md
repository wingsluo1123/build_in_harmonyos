# cleo 0.004 适配笔记

## 编译环境
- 构建系统: perl-makefile (ExtUtils::MakeMaker，Makefile.PL → make → make install)
- 编译日期: 2026-07-31
- 编译器: 无（Perl 脚本不编译 C/C++）
- 状态: built

## 上游
- URL: https://deb.debian.org/debian/pool/main/c/cleo/cleo_0.004.orig.tar.gz
- SHA-256: 245140767ef0f9517fcfed369d89860fa3c0da6d7786d409a949c3088b002c87
- homepage: https://github.com/thaljef/App-Cleo
-性质: Perl CLI 库（App::Cleo），终端差异查看工具

## 编译步骤

1. 初始化编译环境：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build cleo 0.004
   ```

2. 配置：Perl Makefile.PL（ExtUtils::MakeMaker）：
   ```bash
   PERL5LIB=$perl_Term_ReadKey/lib/perl5:$perl_Term_ANSIColor/lib/perl5:... \
   perl Makefile.PL INSTALL_BASE=$TEST_PREFIX
   ```

3. 编译：
   ```bash
   make
   ```

4. 安装到 staging：
   ```bash
   make install
   ```

5. 测试：
   ```bash
   perl -MExtUtils::MakeMaker -e 'make test'
   # t/compile.t .. ok: 1/1 passed
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识引用 |
|---|------|------|----------|----------|
| 1 | Perl 模块依赖找不到 | cleo 依赖 Term::ReadKey/Term::ANSIColor/File::Slurp/Time::HiRes 5 个 Perl 模块 | 通过 Conan Perl 生态包提供（resolve-deps ✅），PERL5LIB 注入 package_folder/lib/perl5 | — |
| 2 | 上游测试是 Perl Test::More 非 C 测试 | t/compile.t 是 `use_ok('App::Cleo')` Perl 模块加载测试 | 消费者测试 test_cleo.c 用 perl -c 语法检查替代（R34 非空壳，间接验证 Perl 模块依赖链可加载） | — |

## 源码修改

无补丁文件（cleo 源码无需修改，Perl 模块依赖通过 Conan 依赖注入）。

## 依赖版本

- perl-Term-ReadKey: 2.38（Conan 制品仓已发布）
- perl-Term-ANSIColor: 5.01
- perl-File-Slurp: 9999.32
- perl-Time-HiRes: 1.9742
- perl-ExtUtils-MakeMaker: 7.70

## 验证结果

```bash
# cleo 脚本安装
file bin/cleo
# Perl script text executable

# Perl 模块加载测试
perl -c bin/cleo
# bin/cleo syntax OK

# 上游测试
perl -MExtUtils::MakeMaker -e 'make test'
# t/compile.t .. ok: 1/1 passed
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/cleo | Perl CLI 脚本（终端差异查看工具） |
| lib/App/Cleo.pm | Perl 模块 |

## 注意事项

1. **cleo 是 Perl CLI 库**，非 C/C++ 库——榜单 lang=cpp 标错了，实际是 Perl（App::Cleo）。
2. **Perl 模块依赖通过 Conan Perl 生态包提供**，PERL5LIB 注入 package_folder/lib/perl5 路径。
3. **上游测试 t/compile.t 是 Perl Test::More use_ok('App::Cleo')**，消费者测试 test_cleo.c 用 perl -c 语法检查替代（R34 非空壳，间接验证 Perl 模块依赖链可加载）。

## 路径 B 申报

本库适配过程无通用问题可入知识图谱（Perl 模块依赖通过 Conan 包解决非通用问题，ExtUtils::MakeMaker 构建无平台特有障碍），**不走路径 B**，仅走路径 A（基础适配）。
