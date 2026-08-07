# perl-io-tty 1.20-r2 适配笔记 (Conan 适配)

## 编译环境
- 构建系统: perl (Makefile.PL)
- 编译日期: 2026-08-07
- 编译器: clang 15.0.4
- 状态: published (conan-verify passed)
- 目标平台: aarch64-unknown-linux-ohos

## Conan 适配

### 配方文件
- conanfile.py: Perl XS 模块配方 (package_type=shared-library)
- conandata.yml: GitHub 源码 URL + SHA256 + 补丁声明
- test_package/: Perl 测试脚本 (test.pl) + conanfile.py + MANIFEST.yml

### 构建命令
```bash
perl Makefile.PL
make OTHERLDFLAGS="-nostartfiles -nodefaultlibs -lc" -j1
```

### 关键适配点
1. **package_type**: 使用 `shared-library` (Perl XS 模块总是 .so)
2. **cwd**: build() 中使用 `cwd=self.source_folder` 确保在源码目录执行
3. **无 conan 依赖**: perl 是系统工具，不在 conan 制品仓中
4. **package_info**: `libs=["Tty"]`, `libdirs=["lib/auto/IO/Tty"]`

## 补丁说明

### 0001-Makefile.PL.patch
1. 硬编码 PTY/TTY 函数检测（绕过 CRT 文件缺失）
2. 函数/头文件检测跳过已硬编码项
3. 编译器检查使用 `-c` (compile-only)
4. **符号检测使用 `-c` 标志** (恢复原始检测逻辑，正确识别未定义符号)
5. 添加 `OTHERLDFLAGS: -nostartfiles -nodefaultlibs -lc`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CRT 文件找不到 | Perl XS 链接时缺少 CRT 文件 | PERL_MM_OPT + OTHERLDFLAGS |
| 2 | 符号检测失败 | 原始检测做完整链接，CRT 缺失导致全部失败 | 使用 -c (compile-only) 标志 |
| 3 | 未定义符号编译错误 | 旧补丁跳过检测，标记所有符号为已定义 | 恢复原始检测逻辑 + -c 标志 |
| 4 | 'reources' 拼写错误 | 旧补丁引入的 typo | 修正为 'resources' |
| 5 | Conan package_type 错误 | library 类型需要 shared 选项 | 改用 shared-library |
| 6 | Makefile.PL 路径找不到 | build() 在 build 子目录执行 | 使用 cwd=self.source_folder |
| 7 | 测试失败 | SELinux HMDFS 限制 | 纯 Perl 模块正常，XS 需系统安装 |

## 验证结果

### Conan 验证 (conan-verify)
- G1 配方完整性: ✅ PASS
- G2 conan create: ✅ PASS
- G3 系统库隔离: ✅ PASS
- G4 产物完整性: ✅ PASS
- L2/L4/L5: ✅ PASS

### 编译产物
- Tty.so: ELF shared object, 64-bit LSB arm64
- Pty.pm: 纯 Perl 模块
- Tty.pm: 纯 Perl 模块
- Constant.pm: 常量定义（自动生成）

---
**Conan 适配日期**: 2026-08-07
**最终状态**: published
