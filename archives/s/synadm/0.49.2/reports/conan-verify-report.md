# Conan Verify Report — synadm 0.49.2

**Verdict**: FAIL
**Reference**: `synadm/0.49.2@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-10-15T18:09:29.333765

## G1: ❌ FAIL
  ✅ name 声明
  ✅ version 声明
  ✅ source() 方法
  ✅ build() 方法
  ✅ package() 方法
  ✅ package_info() 方法
  ❌ conanfile.py 缺少: export_sources() 方法
  ❌ conanfile.py 缺少: 补丁应用调用
  ℹ️ R26: 未检测到静态链接配置（非系统同名库无需静态）
  ✅ conandata.yml 完整
  ✅ test_package/ 存在 (R28)
  ✅ test_package/MANIFEST.yml 存在
