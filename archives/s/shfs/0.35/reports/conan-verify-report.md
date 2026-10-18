# Conan Verify Report — shfs 0.35

**Verdict**: PASS
**Reference**: `shfs/0.35@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-10-17T19:50:19.680944

> 工具产物勘误（两处以事实为准）：
> 1. G0 的「构建系统: autotools」是自动识别误判——本包是裸 `shfsmount/Makefile`，无 configure/autotools，
>    故命中的 E566（config.guess 平台探测）不适用，配方未加 `--build/--host` 是正确选择（`manifest.yaml` 记 `build_system: makefile`）。
> 2. G4 的「无法找到程序包 ID」= 配方尚未 `conan upload` 到制品仓，属预期；因此 `status` 按 R29 口径记 `built`，
>    合并后由发布流水线上传成功再转 `published`。

## G0: ✅ PASS
**Knowledge hit**: E566
  📦 构建系统: autotools
  ⚠️ 已知风险 E566 未在配方中处理
     根因: autotools 的 configure 在未显式传 --build/--host 时会运行 m4/config/config.guess 探测构建平台。该探测在 OHOS worker 上双重失败：(1) config.guess 无法
     方案: explicit-build-host-triplet
     修复: conanfile.py build(): self.run("./configure --prefix=/ --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-o
     ⚡ G2 conan create 可能因此失败，建议先修复

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
  📄 日志: archives/s/shfs/0.35/reports/conan-create.log

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
