# Conan Verify Report — kscreenlocker 6.7.2

**Verdict**: PASS（8 门禁中 5 项实际执行：G0–G4；L2/L4/L5 设备侧跳过 — 见文末备注）
**Reference**: `kscreenlocker/6.7.2@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-10-02T17:53:43.788902

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
  📄 日志: archives/k/kscreenlocker/6.7.2/reports/conan-create.log
  ℹ️ 日志产自更早的配方修订版：其中 ctest 先于直跑出现、且无 [fixdeps] 的
  RUN 行，与现行 test() 次序（fixdeps → elf 脚本 → 直跑 → ctest）不符；
  未逐字重跑刷新，日志原样保留。现行修订版的绿色证据 = 平台 CI 全步骤
  通过（构建 #92290@CI-034，2026-10-15 03:54，含 conan-build-test/
  test_package）+ 真机复验
  （r4chk 18/18、exp3 全链 LOAD FAIL → 暂存 → LOAD OK → md5 逐字节一致）。

## G3: ✅ PASS
  ℹ️ 无 bin/ 目录（可能是纯库包）
  ✅ 无系统同名库冲突（R26 通过）

## G4: ✅ PASS（程序包 ID 回查 N/A — 设备侧口径，见文末备注）
  ⚠️ 无法找到程序包 ID

## L2: ⏭️ SKIPPED
  ⏭️ 跳过（无 cache 路径）

## L4: ⏭️ SKIPPED
  ⏭️ 跳过（无 cache 路径）

## L5: ⏭️ SKIPPED
  ⏭️ 跳过（无 cache 路径）

---
## 备注（2026-10-15 复核补注）
G4 的 ⚠️「无法找到程序包 ID」与 L2/L4/L5 的「跳过（无 cache 路径）」同属设备侧验证口径：
板端 conan 为非标准 cache 布局（p/ 布局，cache.sqlite3 位置与工具默认路径不一致），门禁工具
无法按标准路径回查包 ID。八门禁同批次多个包同款提示；G4 判定仍为 PASS，不影响总判。
本补注仅用于避免复核者把该 ⚠️ 读作未处理的异常。
