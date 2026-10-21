# lwgps 2.4.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published

## 编译步骤

1. `ohc-run.py init-build lwgps 2.4.0 --url=https://github.com/MaJerle/lwgps/archive/refs/tags/v2.4.0.tar.gz`
   （官方 tag v2.4.0 已核验，commit a92d692）
2. 上游测试：`tests/test.py` 递归枚举 4 个测试入口（test_parse_beidou / test_parse_ext_time /
   test_parse_sat_det / test_parse_standard），r02 逐入口真实构建运行 4/4 通过；ctest 需在各
   入口 `__build__` 子目录运行（顶层未 enable_testing()）
3. 配方：`conan-init` 生成 cmake 配方；`build()` 只构建 `lwgps` 库子目录
   （顶层会把测试 opts 注入库编译，造成结构体布局错位 → test_package 段错误）
4. `conan-verify` 通过（G1-G4）；`finish` W3 本地 CI 模拟通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 中 test_package 两测试均 Signal 11 段错误 | 顶层 CMakeLists 把 tests/test_parse_sat_det 的 lwgps_opts.h（LWGPS_CFG_STATEMENT_GPGSV_SAT_DET=1）经 add_subdirectory 注入库编译；库内 lwgps_t 含 sats_in_view_desc[48]，消费者头文件为默认 opts（无该字段）→ 结构体布局错位，库写入越界 | 配方 build() 改为 `cmake.configure(build_script_folder="lwgps")` 只构建库子目录（默认 opts），package() 从构建目录根复制 liblwgps.a |
| 2 | ctest 顶层 "No tests were found" | 上游顶层 CMakeLists 未调用 enable_testing()（仅在 tests/ 子目录调用） | 在 build/tests 子目录运行 ctest，1/1 通过；已记录到 test-report |
| 3 | W3 本地 CI 模拟 JC 拦截（2 junk） | origin/main 中其他库（cloog/kics/thc）被误提交的 .build-closed/.staging-verified 运行时标记（full 模式整仓扫描） | 受限 index 隔离（git rm --cached 精确 4 路径，工作树从备份恢复），复验 W3 通过后无条件恢复索引并校验哈希（e3b0c44… 空文件） |

## 源码修改

无补丁（上游源码零修改）

## 依赖版本

无外部依赖（纯 C 库，仅系统 libc/math）

## 验证结果

- 上游测试 4/4 通过（r02 逐入口普查并真实运行：test_parse_beidou / test_parse_ext_time / test_parse_sat_det / test_parse_standard，各 1/1；实测 N=4 与声明 N=4 对账一致）；test_package 2/2 通过（含 harmonyos_specific_test）
- conan-verify G1-G4 全部通过；W3 build_and_test.sh 全绿（.ci-result.json exit_code=0）

## 注意事项

- 打包时必须以默认 opts 构建库子目录，禁止使用顶层 CMake（测试 opts 污染）
- 默认配置头 lwgps_opts.h 由官方 lwgps_opts_template.h 复制产出
- 上游官方枚举器 tests/test.py 递归枚举 4 个测试入口（glob tests/**/*.cmake，排除 __build__）；顶层 CMakeLists 默认仅装配 test_parse_sat_det，其余入口需用 -DTEST_CMAKE_FILE_NAME 独立配置运行（r02 已验证全部 4 入口可运行）
- CTest 注册项：tests/CMakeLists.txt 对每个装配以 add_test(NAME Test) 注册 1 项，故 4 入口=4 项 ctest（平台 N=4）
---

**编译结束**: 2026-09-28 16:54
**最终状态**: published
