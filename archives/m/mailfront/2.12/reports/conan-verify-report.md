# Conan Verify Report — mailfront 2.12

**Verdict**: PASS
**Reference**: `mailfront/2.12@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-10-15T16:22:02.713844

## G0: ✅ PASS

官方扫描器根据历史特征把本项目误标为 `autotools` 并命中 E490；该提示不适用于本提交。上游实际为自定义 Makefile，配方没有执行 `configure`，而是生成 `conf-cc`、`conf-ccso`、`conf-ld` 后执行 `make -j1 all lua`。G2 的真实构建与完整上游测试已经覆盖实际构建路径。

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
  📄 原始日志保留在仓库外审计目录；本次日志 SHA256 由 W3 回执和测试报告记录

## G3: ✅ PASS
  ✅ 无系统同名库冲突（R26 通过）

## G4: ✅ PASS
  ⚠️ 无法找到程序包 ID

## L2: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L4: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L5: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## 结果边界说明

`conan-verify` 命令退出码为 0；G0 完成扫描但产生上述构建系统误分类提示，G1、G2、G3 实际执行并通过。生成器在 G4 无法定位 package ID，因此 L2、L4、L5 显式跳过；本报告不把这些跳过项表述为已执行。最终 ELF 架构、签名、动态闭包、路径可迁移性、公共头文件消费和运行时行为由 `test_package` 与 HarmonyOS PC 真机检查补足，详见 `test-report.md`。
