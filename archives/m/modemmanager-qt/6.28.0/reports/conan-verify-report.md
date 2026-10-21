# Conan Verify Report — modemmanager-qt 6.28.0

**Verdict**: PASS
**Reference**: `modemmanager-qt/6.28.0@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-10-19T02:38:19.905774

> 说明（人工补充，随档提交）：本报告由 `conan-verify` 自动生成。为避免把未执行项读作实测证据，工具原文中 G4/L2/L4/L5 的 `✅ PASS` 标题已人工改为 `⏭️ NOT EXECUTED`；已执行的 G0/G1/G2/G3 保持工具原判。
> - **G2**：`conan create` 已在真机完整执行并通过（上游 `100% tests passed, 0 tests failed out of 10`，消费者 ctest `0 tests failed out of 1`，消费者直跑 `TEST SUMMARY: 12 passed, 0 failed`）。原始日志 `conan-create.log` 含设备绝对路径，按平台规则不随包提交；实测记录见 `notes.md`。
> - **G4**：runner 未能解析程序包 ID（原文"⚠️ 无法找到程序包 ID"），该项未执行。
> - **L2/L4/L5**：原文"⏭️ 跳过（无 cache 路径）"，均未执行；平台 CI 的完整流水线覆盖这些检查。
> - **L5 补充证据（人工记录）**：`readelf -d lib/libKF6ModemManagerQt.so` 仅有 `SONAME libKF6ModemManagerQt.so`，无 RPATH/RUNPATH 条目（依赖经 `LD_LIBRARY_PATH` 解析）；包内为裸 SONAME 单文件，sha256 `5d954ba22327bdfef5a7a30d9bf8e1043141385e162e35d26a8c0afac3923bd4`。

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
  📄 日志: 原始 conan-create.log 含设备绝对路径，按平台规则不随档（实测记录见 notes.md）

## G3: ✅ PASS
  ℹ️ 无 bin/ 目录（可能是纯库包）
  ✅ 无系统同名库冲突（R26 通过）

## G4: ⏭️ NOT EXECUTED
  ⚠️ 无法找到程序包 ID

## L2: ⏭️ NOT EXECUTED
  ⏭️ 跳过（无 cache 路径）

## L4: ⏭️ NOT EXECUTED
  ⏭️ 跳过（无 cache 路径）

## L5: ⏭️ NOT EXECUTED
  ⏭️ 跳过（无 cache 路径）
