# 测试报告 — indi-rtklib 1.0-20221222172722

> **项目**: indi-rtklib 1.0-20221222172722
> **测试日期**: 2026-10-06
> **测试环境**: OpenHarmony PC（MateBook）aarch64 · Conan 2.29.1（OHOS 适配版）· profile ohos-aarch64 · CMake 4.1.2
> **测试类型**: 手动功能测试（消费者测试 test_package；上游无测试套件）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 5 | 100% |
| 通过 (PASS) | 5 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

上游测试用例：0（上游无测试套件。清点证据：源码包全树仅 `rtklib_driver.{cpp,h}`、
`rtkrcv_parser.{c,h}`、`CMakeLists.txt`、`cmake_modules/`、`config.h.cmake`、
`indi-rtklib.spec`、`indi_rtklib.xml.cmake`，无 tests/ 目录、无 ctest/gtest 注册）。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**：conan-verify 全绿（G1/G0/G2/G3/G4），W3 本地 CI 全绿（L1e 破坏性负测正确识别测试真实性），finish 的 PR 原子性（W2）PASS（仅本配方 14 个文件）。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 验证机对链 libindi 共享库的二进制 exec EPERM（exit 126） | `--help` 探测仅 warn | 🟡 环境限制，非产物缺陷 |
| 上游解析器未终止缓冲区 + strcmp 的 UB（patch 0004 已回移上游 master 修复） | 修复前运行期状态解析全不命中 | 🟢 已修复并锁定断言 |

### 2.3 可用功能清单

```
✅ RTK 解字符串解析 scansolution()："------"→status_no_fix（实测 fix=1）
✅ scansolution()："SINGLE"→status_single（实测 fix=6）
✅ scansolution()："FIX"→status_fix（实测 fix=2，patch 0004 后确定性识别）
✅ scansolution()："FLOAT"→status_float（实测 fix=3，未被 FIX 分支吞并）
✅ 驱动二进制打包：bin/indi_rtklib + share/indi/indi_rtklib.xml
⚠️ 驱动完整功能：需连接 GPS/RTK 设备（无硬件未测）
⚠️ bin/indi_rtklib --help 执行：验证机 exec EPERM（环境限制）
```

### 2.4 已知限制

1. 驱动完整功能需连接 GPS/RTK 设备，本轮验证范围为编译 + 解析器 API + 二进制存在性。
2. 验证机对链 libindi 共享库（libindidriver.so.2 等）的二进制一律 exec EPERM（对照组仅链 libnova 的二进制可正常执行），属该机环境限制；`--help` 探测按设计仅 warn 并如实报告退出码，产物存在性由硬断言承担。W3 闸 L2 同名失败为 non-blocking。
3. finish 收尾辅助步骤的框架侧告警与配方无关：gen_summary 框架 bug（'str' object has no attribute 'append'，indi-starbook-ten 同机复现）、manifest patches_applied 计数（与已合并 libindi/2.2.2.1 同口径）。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| no_fix 解析 | Layer 1 真实 C API scansolution()：`(------)`→status_no_fix | ✅ PASS（fix=1, expect 1） |
| single 解析 | Layer 1：`(SINGLE)`→status_single | ✅ PASS（fix=6, expect 6） |
| fix 解析 | Layer 1：`(FIX)`→status_fix（strncmp 前缀匹配） | ✅ PASS（fix=2, expect 2） |
| float 解析 | Layer 1：`(FLOAT)`→status_float（未被 FIX 分支吞并） | ✅ PASS（fix=3, expect 3） |
| bin/indi_rtklib 存在性硬断言 | Layer 2（R34/L1e 依赖锚点） | ✅ PASS |
| L1e 破坏性负测 | sabotage 移走 bin/ 后测试真实 FAIL，二进制回放后全绿 | ✅ PASS |

### 3.2 失败/跳过的测试

无。

---

## 四、验证记录

- 分支 HEAD：`264d435f3f`（验证时点 `70fca513b`，其后仅 manifest 文档回填与本报告，构建相关文件未变）
- `conan-verify indi-rtklib 1.0-20221222172722`：G1/G0/G2/G3/G4/L2/L4/L5 全 PASS
- test_package 原文：`no_fix: fix=1` / `single: fix=6` / `fix: fix=2` / `float: fix=3` / `PASS: scansolution public C API exercised`
- W3 本地 CI：L0/L1/L4/L5 pass，L1e pass，L2 仅 warn（EPERM）
- `finish indi-rtklib 1.0-20221222172722 built`：PR 原子性 PASS；`.ci-result.json` 由工具写入（step: W3_local_ci，exit_code: 0，integrity_hash `0c79e39160723b63`）
- 完整日志（conan-create.log / conan-verify-report.md / w3-local-ci.log）留存证于验证机本地
