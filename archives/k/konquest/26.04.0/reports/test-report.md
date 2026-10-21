# Test Report — konquest 26.04.0

**Date**: 2026-10-18
**Binary**: `konquest` (application package, armv8/OHOS)
**Log**: `archives/k/konquest/26.04.0/reports/conan-create.log`（conan create “Testing the package” 段）

## 上游测试（N=0）

konquest 26.04.0 tarball 无测试套件：无 `tests/`、`autotests/`、`test/` 目录，
所有 CMakeLists.txt 中无 `add_test()` / `enable_testing()` / `ecm_add_tests()`。
（复核命令：`find konquest-26.04.0.work -iname "*test*" -not -path "*/.*"` → 0 结果；
`grep -in "test|ECMAddTests|enable_testing" CMakeLists.txt` → 无匹配。）

上游 QA 依赖 KDE CI 源码构建（.kde-ci.yml requires-passing-tests-on: Linux/FreeBSD/Windows）。

## 消费者测试（test_package，实际执行于 conan create）

执行方式：`conan create` 的 "Testing the package" 阶段，
`test_package/conanfile.py test() → test.sh <bin/konquest>`，
环境注入 `QT_QPA_PLATFORM=offscreen`、`LD_LIBRARY_PATH`（conan 依赖库目录 + /system/lib64）。

| # | 类型 | 用例 | 结果 |
|---|---|---|---|
| 1 | 断言 | 二进制存在且可执行 | ✅ PASS |
| 2 | 断言 | `konquest --version` 退出码 0 且输出 `konquest 2.4.26040` | ✅ PASS |
| 3 | 断言 | ELF NEEDED 数量 > 0（运行时可链接） | ✅ PASS（23 个 NEEDED） |
| 4 | **非断言（鸿蒙特有）** | OHOS musl loader NEEDED 闭包解析观测：逐项探测 LD_LIBRARY_PATH + /system/lib64 | ℹ️ 观测报告：resolved=23, not-in-path=0（不判定退出码） |

**总计**：断言用例 3 项（通过 3 / 失败 0 / 跳过 0）；鸿蒙特有非断言观测 1 项
（rule12 消费者可行性证据：全部 23 个 NEEDED 条目在 OHOS 运行时路径下可解析，
含 libc++_shared.so、libc.so 于 /system/lib64 命中）。

**结论**：conan create 测试阶段全部通过（"konquest runtime smoke passed"）。
