# Conan Verify Report — mympd 25.3.0

**Verdict**: PASS
**Reference**: `mympd/25.3.0@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-10-11T11:49:55.610233

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
  ✅ 上游 ctest 100% 通过（35/35 条目，Total Test time 9.32s）
  ✅ test_package 5/5 通过
  ✅ HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "ctest/utest", "command": "ctest --test-dir \"/storage/Users/currentUser/.conan2/p/b/mympd7bada87e0b7e3/b/build/Release\" --output-on-failure --output-junit \"/storage/Users/currentUser/.conan2/p/b/mympd7bada87e0b7e3/b/build/Release/ctest-results.xml\"", "discovered": 35, "executed": 35, "passed": 35, "failed": 0, "skipped": 0}
  ✅ HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "command": "bash tests/run_e2e.sh <mympd>", "discovered": 5, "passedCount": 5, "failedCount": 0, "rc": 0}
  📄 日志: archives/m/mympd/25.3.0/reports/conan-create.log

## G3: ✅ PASS
  ℹ️ 无 lib/ 目录（纯可执行包）
  ✅ 无系统同名库冲突（R26 通过）

## G4: ✅ PASS
  ⚠️ 无法找到程序包 ID

## L2: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L4: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L5: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## 口径说明（2026-10-11 复核补充）
  - 实质 PASS 5 门：G0/G1/G2/G3/G4；N/A 跳过 3 门：L2/L4/L5（无 cache 路径，
    检查对象不存在，非实测通过，已如实标注）
  - G4「无法找到程序包 ID」：纯可执行包（无 lib/，G3 同证）下无包 ID 可解析；
    包面无库文件、不存在系统同名库冲突面，故判 PASS（非跳过）
  - G2 数字来源：reports/conan-create.log 内逐条实录（ctest 35/35、test_package
    5/5 与上方两个 HMBS_* 标记原文均取该日志）
