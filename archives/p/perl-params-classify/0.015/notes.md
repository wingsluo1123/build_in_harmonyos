# perl-params-classify 0.015 适配笔记

## 编译环境
- 构建系统: perl-modulebuild (Build.PL, Module::Build)
- 编译日期: 2026-07-03
- 编译器: clang 18.1.8
- 状态: built
- 目标平台: aarch64-unknown-linux-ohos

## 编译步骤

### 1. 源码下载
从 CPAN 下载源码包：
```
URL: https://cpan.metacpan.org/authors/id/Z/ZE/ZEFRAM/Params-Classify-0.015.tar.gz
SHA256: 398ec15cd899fcd8bef3db9ea1748bf631f15f6c32be203e475b67df510a5914
```

### 2. 初始化编译环境
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build perl-params-classify 0.015
```

### 3. 修改 Build.PL (OHOS 平台适配)
修改 Build.PL 中的 cbuilder() 和 have_c_compiler() 方法：
- 覆盖 cbuilder() 创建 ExtUtils::CBuilder 时传入修复后的 Config
- 从 ldflags/lddlflags 移除 -fstack-protector-strong（ld.lld 不支持）
- 添加 -L/system/lib64 -L~/usr/local/lib -lunwind -lc 到 lddlflags
- 添加 -I~/usr/local/include 到 ccflags（musl 头文件路径）
- have_c_compiler() 直接返回 1（跳过编译器检测，已知 clang 可用）

### 4. 配置与编译
```bash
export CPATH=~/usr/local/include
export LIBRARY_PATH=~/usr/local/lib:/system/lib64
perl Build.PL --install_base=$DEFAULT_PREFIX
./Build
```

### 5. 安装
```bash
./Build install --install_base=$DEFAULT_PREFIX
# Staging 安装
./Build install --install_path lib=$TEST_PREFIX/lib
```

### 6. 测试
```bash
./Build test
# 所有测试通过: Files=13, Tests=4746, 3 wallclock secs
# Result: PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ld.lld: error: unknown argument '-fstack-protector-strong' | Perl Config 的 ldflags/lddlflags 中包含 -fstack-protector-strong（编译器标志），ld.lld 不识别 | 在 Build.PL 的 cbuilder() 中覆盖，从 ldflags/lddlflags 移除该标志 |
| 2 | unless(__PACKAGE__->can("cbuilder")) 跳过覆盖 | Module::Build 0.4234 已有 cbuilder() 方法，unless 检查为 true，覆盖被跳过 | 改为直接 `*cbuilder = sub { ... }` 而非 unless 包裹 |
| 3 | Can't locate object method "have_compiler" via package "ExtUtils::CBuilder" | Build 过程中 CBuilder 平台模块加载问题 | have_c_compiler() 直接返回 1，跳过检测 |
| 4 | 缺少 musl C 库头文件 | sys/types.h 等不在默认搜索路径 | cbuilder() 中添加 -I~/usr/local/include 到 ccflags；环境变量 CPATH |
| 5 | 系统库不在链接器默认搜索路径 | libc, libunwind 不在默认路径 | 添加 -L/system/lib64 -L~/usr/local/lib -lunwind -lc 到 lddlflags |
| 6 | Devel::CallChecker 未安装 | 可选依赖，非必需 | Build.PL 已处理：创建空 callchecker0.h，不链接 callchecker 对象 |

## 源码修改

补丁文件: `patches/0001-Build.PL.patch`

修改文件: `Build.PL`

### 变更内容:
1. **cbuilder() 方法直接覆盖**: 创建 ExtUtils::CBuilder 时传入修复后的 Config 副本
   - 从 ldflags/lddlflags 移除 `-fstack-protector-strong`
   - 添加 `-L/system/lib64 -L$HOME/usr/local/lib -lunwind -lc` 到 lddlflags
   - 添加 `-I$HOME/usr/local/include` 到 ccflags（musl 头文件路径）
2. **have_c_compiler() 直接返回 1**: 跳过编译器检测（OHOS 上已知 clang 可用）
3. 移除 `unless(__PACKAGE__->can("cbuilder"))` 和 `unless(__PACKAGE__->can("have_c_compiler"))` 包裹

## 依赖版本

- perl 5.42.0
- Module::Build 0.4234
- ExtUtils::CBuilder 0.280242
- ExtUtils::ParseXS (系统自带)
- musl C 库头文件: ~/usr/local/include (371 个文件)

## 验证结果

```
./Build test
# All tests successful.
# Files=13, Tests=4746,  3 wallclock secs
# Result: PASS

# Conan 验证
# G1: PASS (配方完整性)
# G2: PASS (conan create 干净构建)
# G3: PASS (系统同名库隔离)
# G4: PASS (产物完整性)
```

## 产物

| 文件 | 说明 |
|------|------|
| blib/arch/auto/Params/Classify/Classify.so | XS 共享库 (ELF 64-bit ARM64) |
| blib/lib/Params/Classify.pm | Perl 模块文件 |
| blib/arch/auto/Params/Classify/Classify.bs | 引导文件 |

## 注意事项

- 本模块使用 Module::Build (Build.PL) 而非 ExtUtils::MakeMaker (Makefile.PL)
- OHOS 平台上 Module::Build 0.33+ 已有 cbuilder() 方法，原代码的 unless 检查会导致覆盖被跳过
- SELinux HMDFS 限制：XS .so 从 ~/usr/local/lib 加载可能受限，需安装到系统目录
- Devel::CallChecker 为可选依赖，缺失时不影响编译

---
**编译结束**: 2026-07-03 16:52
**最终状态**: built (编译成功，测试通过，Conan 验证通过)
