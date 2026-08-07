# Conan Verify Report — open-adventure 1.20

**Verdict**: FAIL
**Reference**: `open-adventure/1.20@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-08-07T07:59:12.793908

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
  ✅ R26: 系统同名库静态链接配置存在
  ✅ conandata.yml 完整
  ✅ test_package/ 存在 (R28)
  ✅ test_package/MANIFEST.yml 存在

## G2: ❌ FAIL
**Knowledge hit**: E165
  ❌ conan create 失败:
     ERROR: open-adventure/1.20@ohpcd/stable (test package): Error in build() method, line 21
  📄 日志: archives/o/open-adventure/1.20/reports/conan-create.log
    🧠 知识图谱命中: E165 (评分:1240)
     根因: OpenHarmony 系统没有传统的 /bin 目录，bash 位于 /data/service/hnp/bin/bash，sh 位于 /system/bin/sh。脚本 shebang 指向不存在的路径导致脚本无法执行。
     方案: shebang-fix
     命令: sed -i '1s|#!/bin/bash|#!/data/service/hnp/bin/bash|' configure; sed -i '1s|#!/bin/sh|#!/system/bin/sh|' install.sh shor
     文档: doc/E165.md
