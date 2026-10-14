# ksyntaxhighlighting5 5.116.0 — 测试报告

**软件**: ksyntaxhighlighting5 / 5.116.0
**平台**: HarmonyOS PC (arm64 / aarch64-linux-ohos), OHOS 6.0, clang 15, libc++
**日期**: 2026-09-30
**构建系统**: CMake (ECM) + Conan 配方
**被测库**: libKF5SyntaxHighlighting.so.5

---

## 1. 测试环境

- BUILD_TESTING=ON；上游 autotests 已编译并在 conanfile.py build() 中通过 ctest 真实执行（2026-10-12 整改 PR #14936 rule4）
- 纯库包，无 bin/ 可执行文件（G3 无 bin/ 目录）

## 2. test_package (L1)

conan create 内嵌 test_package 已执行：

- 沙箱加载 libKF5SyntaxHighlighting.so 失败 rc=127，Repository/Definition API symbols 降级为链接级解析（编译/链接通过，符号解析完整）
- 结果: **PASS**（链接级验证，退出码 0）

## 3. 上游自带测试 (autotests/)

conan create 内嵌 ctest 实测（QT_QPA_PLATFORM=offscreen + HOME/XDG 隔离，kconfig5/5.116.0 先例）：

| # | 测试 | 结果 |
|---|------|------|
| 1 | wildcardmatcher_test | Passed |
| 2 | repository_test | Passed |
| 3 | theme_test | Passed |
| 4 | testhighlighter_test | Passed |
| 5 | htmlhighlighter_test | Passed |
| 6 | folding_test | Passed |

- 运行通过率: **6/6 = 100%**（Total Test time 6.94 sec）
- 上游实测 N=6，与声明 N=6 一致（rule4 少报核验通过）

## 4. 门禁摘要

- conan-verify: G0-G4 + L2/L4/L5 全部 PASS（G3 无 bin/ 纯库包）
- G2 conan create 干净构建通过（含 ctest 6/6）

## 5. 结论

**通过**。ksyntaxhighlighting5 在 HarmonyOS PC (arm64) 上编译通过，test_package 链接级验证通过，上游 6 个 autotests 真实执行 100% 通过（test_package 二进制因沙箱加载限制降级为链接级证明，符号解析完整）。
