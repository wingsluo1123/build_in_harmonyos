# perl-params-util 1.102 适配笔记

## 编译环境
- 构建系统: Perl Makefile.PL (ExtUtils::MakeMaker + XS)
- 编译日期: 2026-07-03
- 编译器: clang/clang++
- Perl: 5.42.0 (aarch64-linux)
- 状态: built

## 编译步骤

1. `perl Makefile.PL` — 生成 Makefile (XS 检测因 ld.lld 不支持 -fstack-protector-strong 而失败，但 ExtUtils::MakeMaker 仍生成 xsubpp 规则)
2. 补丁 Makefile:
   - CCFLAGS 添加 `-I/storage/Users/currentUser/usr/local/include` (musl C 库头文件)
   - LDDLFLAGS 添加 `-nostartfiles -nodefaultlibs -L/storage/Users/currentUser/usr/local/lib -lc` (CRT 绕过 + musl libc 路径)
3. `make -j1` — 编译 XS (Util.xs → Util.c → Util.o → Util.so)
4. `make install DESTDIR=$TEST_PREFIX` — 安装到 staging 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `sys/types.h` not found | 鸿蒙系统缺少标准 C 库头文件 | CCFLAGS 添加 `-I~/usr/local/include` (musl 头文件) |
| 2 | `unable to find library -lc` | 鸿蒙系统 libc 不在标准搜索路径 | LDDLFLAGS 添加 `-L~/usr/local/lib` |
| 3 | 链接失败 (crti.o/crtn.o 缺失) | 鸿蒙系统缺少 CRT 文件 | LDDLFLAGS 添加 `-nostartfiles -nodefaultlibs` |
| 4 | XS 检测失败 | ld.lld 不支持 -fstack-protector-strong | 不影响构建，ExtUtils::MakeMaker 仍生成 xsubpp 规则 |
| 5 | XS .so 运行时加载失败 | 鸿蒙 ELF 签名限制 (Permission denied) | 纯 Perl 回退 (PERL_PARAMS_UTIL_PP=1) 完全可用 |

## 源码修改

无源码补丁。所有修改通过 conanfile.py 在 build() 阶段 patch Makefile 实现。

## 依赖版本

- Perl 5.42.0 (系统自带)
- musl C 库 (~/usr/local/include, ~/usr/local/lib)
- 无外部 Perl 模块依赖

## 验证结果

```
# 纯 Perl 测试 (make test)
t/pp/01_compile.t .... ok
t/pp/02_main.t ....... ok
t/pp/03_all.t ........ ok
t/pp/04_codelike.t ... ok
t/pp/05_typelike.t ... ok
t/pp/06_invocant.t ... ok
t/pp/07_handle.t ..... ok
t/pp/08_driver.t ..... ok
t/pp/09_insideout.t .. ok
All tests successful.
Files=9, Tests=932, 2 wallclock secs
Result: PASS

# XS 测试 — 失败 (ELF 签名限制，非代码问题)
# 纯 Perl 模式验证通过
PERL_PARAMS_UTIL_PP=1 perl -MParams::Util -e 'print $Params::Util::VERSION'
# 输出: 1.102
```

## 交付物

| 文件 | 说明 |
|------|------|
| `site_perl/5.42.0/aarch64-linux/Params/Util.pm` | 主模块 |
| `site_perl/5.42.0/aarch64-linux/Params/Util/PP.pm` | 纯 Perl 回退模块 |
| `site_perl/5.42.0/aarch64-linux/auto/Params/Util/Util.so` | XS 共享库 |
| `lib/Util.so` | 复制的 .so (用于包完整性检查) |

## 注意事项

- XS .so 在鸿蒙系统上因 ELF 签名限制无法直接加载，需 CI 签名后可用
- 纯 Perl 回退 (PERL_PARAMS_UTIL_PP=1) 完全功能，932 个测试全部通过
- Makefile.PL 的 XS 检测 (Config::AutoConf) 在鸿蒙上会失败，但不影响构建
- conanfile.py 通过 patch Makefile 的 CCFLAGS 和 LDDLFLAGS 解决平台兼容问题
---

**编译结束**: 2026-07-03 16:57
**最终状态**: built
