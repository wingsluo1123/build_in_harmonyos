# perl-params-validate 1.31 编译笔记

## 编译环境
- 构建系统: Perl Module::Build (Build.PL)
- 编译日期: 2026-07-03
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 CPAN 下载 Params-Validate-1.31.tar.gz
2. 初始化编译环境：ohc-run.py init-build perl-params-validate 1.31
3. 修改 inc/MyMBClass.pm 覆盖 cbuilder() 方法（修复 E137）
4. 运行 perl Build.PL 配置
5. 运行 ./Build 编译
6. 运行 ./Build install --destdir=$TEST_PREFIX 安装到 staging

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接错误：ld.lld 拒绝 -fstack-protector-strong | Perl 5.42.0 的 lddlflags 包含该参数 | 覆盖 cbuilder() 移除 -fstack-protector-strong (E137) |
| 2 | 缺少 stdio.h 等 C 标准库头文件 | 鸿蒙系统默认搜索路径无 musl 头文件 | 通过 ccflags 添加 -I~/usr/local/include |
| 3 | 链接找不到 libc | 系统库不在默认搜索路径 | 通过 lddlflags 添加 -L~/usr/local/lib -L/system/lib64 |
| 4 | 链接器使用了 ld.lld 而非 clang | 环境变量 LD 设置 | 强制设置 config{ld} = "clang" |
| 5 | SELinux HMDFS 限制 XS 模块加载 | hishell_hap domain 只能加载 hnp_file 类型 | 需安装到系统目录 /data/service/hnp |

## 与 perl-dbd-pg 编译经验对比

| 维度 | perl-dbd-pg | perl-params-validate |
|------|------------|---------------------|
| 构建系统 | ExtUtils::MakeMaker (Makefile.PL) | Module::Build (Build.PL) |
| CRT 缺失修复 | dynamic_lib => OTHERLDFLAGS | cbuilder() 配置覆盖 |
| 头文件路径 | INC 参数 | ccflags -I 参数 |
| 库路径 | LIBS 参数 | lddlflags -L 参数 |
| 链接器 | LD = clang | config{ld} = "clang" |
| SELinux 限制 | 相同 | 相同 |

### 关键差异
- perl-dbd-pg 使用 Makefile.PL (ExtUtils::MakeMaker)，通过 `dynamic_lib => { OTHERLDFLAGS => '-nostartfiles -nodefaultlibs -lc' }` 绕过 CRT 缺失
- perl-params-validate 使用 Build.PL (Module::Build)，通过覆盖 `inc/MyMBClass.pm` 的 `cbuilder()` 方法修复链接器配置
- 两者都需要 musl C 库头文件和系统库路径
- 两者都受 SELinux HMDFS 限制，XS 模块需安装到系统目录

## 依赖版本

### 已存在
- perl: 5.42.0 (系统安装, /data/service/hnp/perl.org/perl_5.42.0/)
- musl C 库头文件: ~/usr/local/include (371 个文件)
- Module::Build: 随 perl 5.42.0 提供

### 编译依赖
- musl C 库头文件（提供 stdio.h, ctype.h, sys/types.h 等）
- clang 编译器 (/data/service/hnp/bin/clang)

## 编译产物

- **XS.so**: 50,688 bytes，ELF 64-bit AArch64 共享对象
  - 路径: blib/arch/auto/Params/Validate/XS/XS.so
  - 动态依赖: libc.so
  - ELF 安全: NX 栈不可执行 (RW), GNU_RELRO 启用
  - 关键符号: boot_Params__Validate, validate, validate_pos, validate_one_param
  - SELinux context: u:object_r:hmdfs:s0
- **Validate.pm**: 26,713 bytes，Perl 模块文件 (主入口)
- **ValidatePP.pm**: 156 bytes，PP 实现入口
- **ValidateXS.pm**: 156 bytes，XS 实现入口
- **PP.pm**: 20,313 bytes，纯 Perl 实现细节
- **Constants.pm**: 552 bytes，常量定义

## 知识沉淀

### 平台发现
- Perl 5.42.0 on OHOS 的 lddlflags 包含 -fstack-protector-strong (E137)
- Module::Build 的 cbuilder() 方法可覆盖 ExtUtils::CBuilder 配置
- 鸿蒙系统库在 /system/lib64
- musl C 库头文件需手动指定路径

### 编译建议
- Perl XS 模块编译需要完整的 C 库头文件支持 (musl)
- Module::Build 系统通过覆盖 inc/ 下的自定义类可实现平台适配
- 需要 ELF 签名才能在鸿蒙系统执行

---

## 功能测试结果 (2026-07-06)

### PP (纯 Perl) 模式: 全部通过 (10/10)

| # | 测试项 | 状态 |
|---|--------|------|
| 1 | validate: 必需参数 (foo) | PASS |
| 2 | validate: 必需参数 (bar) | PASS |
| 3 | validate: 可选参数默认值 | PASS |
| 4 | validate: 缺少必需参数报错 | PASS |
| 5 | validate_pos: 位置参数 | PASS |
| 6 | validate_pos: 位置参数 | PASS |
| 7 | validate: 正则约束匹配 | PASS |
| 8 | validate: 正则约束失败报错 | PASS |
| 9 | validate_with 函数导出 | PASS |
| 10 | validate: ARRAYREF 类型 | PASS |

### XS 模式: SELinux 限制

- 直接加载 XS.so 失败: Permission denied (hmdfs:s0)
- Module::Implementation 自动降级到 PP 模式
- 需安装到系统目录 `/data/service/hnp` 才能使用 XS 模式
- XS.so 签名失败: 无 .codesign section

### 结论

PP 模式完全可用，XS 模式需管理员安装到系统目录。通过 Module::Implementation 自动降级机制确保功能可用性。

---
**编译结束**: 2026-07-03 16:58
**功能测试**: 2026-07-06
**最终状态**: built (编译成功，conan-verify 通过，PP 模式功能测试全部通过)
