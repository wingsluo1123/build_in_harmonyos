# wifi-qr 0.4 — 本地测试报告 (W3 / R51)

- 日期: 2026-10-17
- 平台: 鸿蒙PC aarch64 (aarch64-linux-ohos), 本机真机
- 验证: `conan create -pr:h=ohos-aarch64 --build=missing`（conan-verify G2）

## 上游测试清点（R51 三步法）
- 上游无 tests/ 目录、无 ctest/pytest；Makefile `test-install` 仅安装演练。
- 结论: 上游测试 0/0（N/A），以 test_package 消费者测试代替。

## test_package 实测（conan create 自动执行）
| # | 用例 | 命令 | 期望 | 结果 |
|---|------|------|------|------|
| 1 | 版本横幅 | `wifi-qr -v` | stdout 含 "WiFi-QR 0.4"，exit 0 | ✅ PASS |
| 2 | 用法输出 | `wifi-qr -h \| head -1` | stdout 含 "Usage:"，exit 0 | ✅ PASS |

- 通过率: 2/2 = 100%
- 运行环境: VirtualRunEnv（qrencode/4.1.1、zbar/0.23.93 随依赖进入 PATH）

## 平台适配转换
- shebang `#!/bin/bash` → `#!/usr/bin/env bash`（鸿蒙PC 无 /bin/bash，package() 内转换）
- 上游源码 0 修改、0 补丁

## 结论
- G1-G4、L2/L4/L5 全部 PASS（reports/conan-verify-report.md）
- W3 本地 conan create 通过，`.ci-result.json` 由 finish 自动写入
