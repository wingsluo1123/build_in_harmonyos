# Conan Verify Report — perl-b-cow 0.007

**Verdict**: PASS
**Reference**: `perl-b-cow/0.007@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-10-12T12:11:30.479103

## G0: ✅ PASS
  📦 构建系统: unknown
  ℹ️ 无法识别构建系统，跳过预查询

## G1: ✅ PASS
  ✅ name 声明
  ✅ version 声明
  ✅ source() 方法
  ✅ build() 方法
  ✅ package() 方法
  ✅ package_info() 方法
  ✅ export_sources() 方法
  ✅ 补丁应用调用
  ℹ️ R26: 未检测到静态链接配置（非系统同名库无需静态）
  ✅ conandata.yml 完整
  ✅ test_package/ 存在 (R28)
  ✅ test_package/MANIFEST.yml 存在

## G2: ✅ PASS
  ✅ conan create 成功
  📄 日志: archives/p/perl-b-cow/0.007/reports/conan-create.log

## G3: ✅ PASS
  ℹ️ 无 bin/ 目录（可能是纯库包）
  ✅ 无系统同名库冲突（R26 通过）

## G4: ✅ PASS
  ✅ lib/: 0 .a + 0 .so

## L2: ✅ PASS
  ℹ️ 无 bin/ 目录（纯库包，跳过 smoke test）

## L4: ✅ PASS
  ℹ️ 无 bin/ 目录，检查 lib/ 中的 .so
  ℹ️ 无可扫描的 ELF 文件

## L5: ✅ PASS
  ✅ 首次运行，基线已保存: archives/p/perl-b-cow/0.007/reports/baseline.json
  📦 10 个文件
