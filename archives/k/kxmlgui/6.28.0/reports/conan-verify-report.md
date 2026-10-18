# Conan Verify Report — kxmlgui 6.28.0

**Verdict**: PASS
**Reference**: `kxmlgui/6.28.0@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-10-18T14:55:39.988313

> 说明（人工补充，随档提交）：本报告由 `conan-verify` 自动生成，下文各门禁的"✅ PASS"表示该门禁未报失败；下列三项为未执行或未解析，不应理解为实测通过：
> - **G2**：`conan create` 已在真机完整执行并通过（上游 ctest 6/6 程序全数 Passed，test_package 6/6 用例通过）。`conan-create.log` 为真机原始日志（56145 字节），依平台规则不随包提交。
> - **G4**：runner 未能解析程序包 ID（原文"⚠️ 无法找到程序包 ID"），该项为未执行。
> - **L2/L4/L5**：原文"⏭️ 跳过（无 cache 路径）"，均为未执行；平台 CI 的完整流水线覆盖这些检查。

## G0: ✅ PASS
  📦 构建系统: cmake
  ✅ 已知风险 E092 已在配方中处理
     CMake 不认识 HarmonyOS 作为目标平台，
没有对应的 platform module。
当 CMake 检测到系统名称为 harmonyos/ohos 时，
无法匹配任何已知平台（Lin

## G1: ✅ PASS
  ✅ name 声明
  ✅ version 声明
  ✅ source() 方法
  ✅ build() 方法
  ✅ package() 方法
  ✅ package_info() 方法
  ✅ export_sources() 方法
  ✅ 补丁应用调用
  ✅ R26: 系统同名库静态链接配置存在
  ✅ conandata.yml 完整
  ✅ test_package/ 存在 (R28)
  ✅ test_package/MANIFEST.yml 存在

## G2: ✅ PASS
  ✅ conan create 成功
  📄 日志: archives/k/kxmlgui/6.28.0/reports/conan-create.log

## G3: ✅ PASS
  ℹ️ 无 bin/ 目录（可能是纯库包）
  ✅ 无系统同名库冲突（R26 通过）

## G4: ✅ PASS
  ⚠️ 无法找到程序包 ID

## L2: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L4: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L5: ✅ PASS
  ⏭️ 跳过（无 cache 路径）
