# perl-crypt-eksblowfish 0.009-r15 编译笔记

## 编译环境
- 构建系统: Perl Module::Build (Build.PL)
- 编译日期: 2026-07-03（首次），2026-07-07（归档完善）
- 编译器: clang/clang++
- 状态: built (conan-verify 全部门禁通过)

## 编译步骤

1. 从 CPAN 下载 Crypt-Eksblowfish-0.009.tar.gz
2. 初始化编译环境：ohc-run.py init-build perl-crypt-eksblowfish 0.009-r15
3. 修改 Build.PL 清理 ldflags 中的 -fstack-protector-strong（ld.lld 不支持，E137）
4. 设置 CPATH/LIBRARY_PATH 指向 OHOS SDK sysroot（musl 头文件）
5. 运行 perl Build.PL 生成 Build 脚本
6. 运行 perl Build 编译
7. 运行 perl Build install 安装到 staging

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接错误：ld.lld 不识别 -fstack-protector-strong | OHOS 使用 ld.lld，不支持 GCC 特有的 -fstack-protector-strong 标志 (E137) | 在 Build.PL 中添加 Config 清理逻辑，通过 config 参数传递给 Module::Build |
| 2 | 缺少 C 库头文件 | 鸿蒙系统默认头文件路径不包含 musl 头文件 | 设置 CPATH 指向 OHOS SDK sysroot 的 usr/include |
| 3 | 缺少 Perl 模块路径 | Module::Build 需要找到已安装的 Perl 模块 | 设置 PERL5LIB 包含用户安装路径和系统路径 |
| 4 | SELinux HMDFS 限制 | 动态库加载受限（hmdfs:s0 上下文被 dlopen 拒绝） | 需安装到系统目录 /data/service/hnp |
| 5 | 归档目录缺失关键文件 | finish 步骤完成后未正确保存 conanfile.py 等文件 | 从 Conan 缓存恢复并改进，创建所有缺失文件 |
| 6 | R6 违规：运行时修改生成的 Build 脚本 | 原配方在 build() 中直接修改生成的 Build 脚本 | 创建 Build.PL 补丁替代运行时修改 |
| 7 | R32/R33 违规 | 原配方缺少 OS 检查且使用硬编码路径 | 添加 OS 检查和动态路径发现方法 |

## 依赖版本

### 已存在
- Perl: 5.42.0 (aarch64-linux, /data/service/hnp/perl.org/perl_5.42.0/)
- musl C 库头文件: OHOS SDK sysroot (stdio.h, ctype.h, sys/types.h 等)
- Module::Build: Perl 核心模块
- ExtUtils::CBuilder: Perl 核心模块 (>= 0.15)
- Class::Mix: 0.001 (用户安装)
- MIME::Base64: 2.21+ (Perl 核心)
- XSLoader: Perl 核心

### 编译依赖
- OHOS SDK sysroot（提供 musl C 库头文件）
- Perl 5.42.0（提供 perl 二进制和核心模块）

## 编译产物

- **Eksblowfish.so**: 39KB，ELF 64-bit ARM64 共享对象
  - NEEDED: libc.so
  - 安全特性: NX + PIE (DYN) + RELRO + BIND_NOW
  - 导出符号: boot_Crypt__Eksblowfish
- **Eksblowfish.pm**: 主模块文件 (4565 bytes)
- **Bcrypt.pm**: bcrypt 哈希实现 (5013 bytes)
- **Blowfish.pm**: 标准 Blowfish 加密 (4061 bytes)
- **Family.pm**: 密码族管理 (6410 bytes)
- **Subkeyed.pm**: 子密钥支持 (6935 bytes)
- **Uklblowfish.pm**: 无密钥 Blowfish (5729 bytes)

## 与 perl-dbd-pg 编译经验对比

| 维度 | perl-dbd-pg | perl-crypt-eksblowfish |
|------|-------------|----------------------|
| 构建系统 | ExtUtils::MakeMaker (Makefile.PL) | Module::Build (Build.PL) |
| 链接问题 | 缺少 CRT 文件 | ld.lld 不支持 -fstack-protector-strong (E137) |
| 链接修复 | OTHERLDFLAGS => '-nostartfiles -nodefaultlibs -lc' | config => { ldflags/lddlflags 清理 } |
| Sysroot 设置 | CPATH/LIBRARY_PATH | CPATH/LIBRARY_PATH (相同) |
| SELinux 限制 | 相同 | 相同 |
| 补丁方式 | 修改 Makefile.PL | 修改 Build.PL |
| R32 合规 | ✅ | ✅ |
| R33 合规 | ✅ | ✅ |
| R6 合规 | ✅ (补丁 Makefile.PL) | ✅ (补丁 Build.PL) |
| Conan verify | ✅ PASS | ✅ PASS |

## 知识沉淀

### 平台发现
- OHOS ld.lld 不支持 GCC 的 -fstack-protector-strong 标志 (E137)
- Module::Build 的 config 参数可有效覆盖 Perl Config 中的链接器标志
- Build.PL 补丁方式优于运行时修改生成的 Build 脚本（符合 R6 规则）
- SELinux 限制：hmdfs:s0 上下文的 .so 文件无法通过 dlopen 加载

### 编译建议
- Perl Module::Build 模块编译需要清理不兼容的链接器标志
- 通过 Build.PL 的 config 参数传递清理后的 ldflags 是推荐做法
- CPATH/LIBRARY_PATH 设置是 OHOS 平台 Perl XS 编译的通用模式
- 需要 ELF 签名才能在鸿蒙系统执行

### 上库评估
- ✅ conanfile.py 完整且通过 conan-verify (G0-G4, L2-L5)
- ✅ conandata.yml 包含源码 URL、SHA256 和补丁声明
- ✅ test_package/ 包含 conanfile.py 和 MANIFEST.yml
- ✅ patches/ 包含 0001-Build.PL.patch
- ✅ manifest.yaml 包含完整编译元数据
- ✅ notes.md 包含编译笔记和知识沉淀
- ✅ reports/ 包含 conan-verify-report.md、conan-create.log、test-report.md
- ✅ R6: 补丁源文件 (Build.PL)，不修改生成文件
- ✅ R27: 依赖引用使用 @ohpcd/stable（无外部依赖）
- ✅ R28: test_package/ 存在
- ✅ R32: settings.os 判断使用 `in ("Linux", "OHOS")`
- ✅ R33: 不依赖未定义的 shell 环境变量

---
**编译结束**: 2026-07-03 11:54
**最终状态**: built (编译成功，产物完整)
**归档完善**: 2026-07-07 (R6/R32/R33 合规化，创建 Build.PL 补丁，完善所有归档文件)
**测试完成**: 2026-07-07 (conan-verify PASS, 功能测试完成，SELinux 限制已记录)
