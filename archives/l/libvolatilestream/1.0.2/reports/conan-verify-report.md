# Conan Verify Report — libvolatilestream 1.0.2

**Verdict**: PASS（限定：G4 未执行包内容校验；L2/L4/L5 因无 cache 路径跳过）
**Reference**: `libvolatilestream/1.0.2@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-10-19T01:28:28.565996

## G0: ✅ PASS
  📦 构建系统: cmake
  ✅ 知识图谱未发现已知风险

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
  📄 日志: archives/l/libvolatilestream/1.0.2/reports/conan-create.log（仅本机保留，不随档）

## G3: ✅ PASS
  ℹ️ 无 bin/ 目录（可能是纯库包）
  ✅ 无系统同名库冲突（R26 通过）

## G4: ⚠️ NOT RUN
  ⚠️ 无法找到程序包 ID
  ℹ️ 本次未执行包内容校验（校验器未取得程序包 ID）；原工具输出为 PASS（未报错），本报告按实际执行情况标注为 NOT RUN。

## L2: ⏭️ SKIP
  ⏭️ 跳过（无 cache 路径）

## L4: ⏭️ SKIP
  ⏭️ 跳过（无 cache 路径）

## L5: ⏭️ SKIP
  ⏭️ 跳过（无 cache 路径）
