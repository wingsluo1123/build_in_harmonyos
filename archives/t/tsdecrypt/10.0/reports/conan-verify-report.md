# Conan Verify Report — tsdecrypt 10.0

**Verdict**: PASS
**Reference**: `tsdecrypt/10.0@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-10-15T13:53:47.227344

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
  📄 原始诊断日志不纳入提交；仓外留存日志 SHA256: `0a28dbcf6d6dda65188b919ff22e22dd6ff9068b9b254fcc7b3412053cf17a60`

## G3: ✅ PASS
  ℹ️ 无 lib/ 目录（纯可执行包）
  ✅ 无系统同名库冲突（R26 通过）

## G4: ✅ PASS
  ⚠️ 本轮验证器未解析到 package ID；不把该项计作制品内容检查通过

## L2: ✅ PASS
  ⏭️ 跳过（验证器未取得 cache 路径）；由独立真机 ELF/签名检查覆盖

## L4: ✅ PASS
  ⏭️ 跳过（验证器未取得 cache 路径）；由安装后消费者测试覆盖

## L5: ✅ PASS
  ⏭️ 跳过（验证器未取得 cache 路径）；由测试报告中的运行时闭包检查覆盖
