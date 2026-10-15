# 测试报告 — indi-starbook-ten 0.1

> **项目**: indi-starbook-ten 0.1
> **测试日期**: 2026-10-06
> **测试环境**: OpenHarmony PC（MateBook）aarch64 · Conan 2.29.1（OHOS 适配版）· profile ohos-aarch64 · CMake 4.1.2
> **测试类型**: 手动功能测试（消费者测试 test_package；上游无测试套件）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 7 | 100% |
| 通过 (PASS) | 7 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

上游测试用例：0（上游无测试套件。清点证据：源码包全树仅 `indi_starbook_ten.{cpp,h}`、
`starbook_ten.{cpp,h}`、`connectionhttp.{cpp,h}`、`httplib.h`、`CMakeLists.txt`、
`cmake_modules/` 及文档/打包文件，无 tests/ 目录、无 ctest/gtest 注册）。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**：conan-verify 全绿（G1/G0/G2/G3/G4），W3 本地 CI 通过（L1e 破坏性负测正确识别测试真实性），finish 的 JC6 单软件原子性 PASS。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 验证机对链 libindi 共享库的二进制 exec EPERM（exit 126） | `--help` 探测仅 warn | 🟡 环境限制，非产物缺陷 |

### 2.3 可用功能清单

```
✅ 协议客户端 getFirmwareVersion()：<!--VERSION=..--> 正则解析（mock 实测 5.10）
✅ 协议客户端 getStatus()：RA/DEC/GOTO/STATE 结构化解析（mock 实测）
✅ 协议客户端 getPierSide()：枚举映射（mock 实测）
✅ 协议客户端 stop()：<!--OK--> 命令应答（mock 实测）
✅ 驱动二进制打包：bin/indi_starbook_ten + share/indi/indi_starbook_ten.xml
⚠️ 驱动完整功能：需连接真实 Vixen StarBook Ten mount（无硬件未测）
⚠️ bin/indi_starbook_ten --help 执行：验证机 exec EPERM（环境限制）
```

### 2.4 已知限制

1. 驱动完整功能需连接真实 Vixen StarBook Ten mount，本轮验证范围为编译 + mock 协议 API + 二进制存在性。
2. 验证机对链 libindi 共享库（libindidriver.so.2 等）的二进制一律 exec EPERM（对照组仅链 libnova 的二进制可正常执行），属该机环境限制；`--help` 探测按设计仅 warn 并如实报告退出码，产物存在性由硬断言承担。W3 闸 L2 同名失败为 non-blocking。
3. finish 收尾辅助步骤的框架侧告警与配方无关：gen_summary 框架 bug（'str' object has no attribute 'append'）、manifest patches_applied 计数（与已合并 libindi/2.2.2.1 同口径）。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| getFirmwareVersion 解析 | Layer 1 mock mount 真实 HTTP 回路 | ✅ PASS（firmware: 5.10, expect 5.10） |
| getStatus 解析 | Layer 1 mock mount | ✅ PASS |
| getPierSide 枚举映射 | Layer 1 mock mount | ✅ PASS |
| stop 命令应答 | Layer 1 mock mount | ✅ PASS |
| （以上合计 6 条断言） | `PASS: StarbookTen public API exercised against mock mount` | ✅ 6/6 |
| bin/indi_starbook_ten 存在性硬断言 | Layer 2（R34/L1e 依赖锚点） | ✅ PASS |
| L1e 破坏性负测 | sabotage 移走 bin/ 后测试真实 FAIL → 闸判"测试真实依赖包产物" | ✅ PASS |

### 3.2 失败/跳过的测试

无。

---

## 四、验证记录

- 分支 HEAD：`ea8686803b`（验证时点 `dbfd1f99f`，其后仅 manifest 文档回填与本报告，构建相关文件未变）
- `conan-verify indi-starbook-ten 0.1`：G1/G0/G2/G3/G4 全 PASS
- W3 本地 CI：L0/L1/L4/L5 pass，L1e pass，L2 skip（non-blocking warn，EPERM）
- `finish indi-starbook-ten 0.1 built`：JC6 PASS（涉及软件数 1）；`.ci-result.json` 由工具写入（step: W3_local_ci，exit_code: 0，integrity_hash `c623a40be242e398`）
- 完整日志（conan-create.log / conan-verify-report.md / w3-local-ci.log）留存证于验证机本地
