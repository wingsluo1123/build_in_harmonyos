# physlock 13 — 测试与验证报告

- 日期：2026-10-13
- 包引用：`physlock/13@ohpcd/stable`（profile `ohos-aarch64`）
- 构建/测试命令（真实、逐条）见下方"命令与退出码"

## 一、上游测试（单独汇报）

| 指标 | 值 |
|------|-----|
| 上游自动化测试入口 | **不存在**（无 `tests/`、Makefile 无 `check`/`test` 目标，见 `upstream-test-entry.md`） |
| 上游测试用例总数 | **0** |
| 通过 / 失败 / 跳过 | **0 / 0 / 0**（无测试套件） |
| 上游样例（README 文档化入口）用例总数 | **3** |
| 上游样例 通过 / 失败 / 跳过 | **3 / 0 / 0** |
| 不可测项 | 1（真机锁屏路径：需 root + `/dev/tty0` + `/etc/pam.d/physlock`，沙箱不可测，如实记录不伪装通过） |

上游样例逐项名称（均实际执行，命令与原始输出见 `notes.md`）：

1. `upstream-version-v`（`physlock -v` → `physlock 13`，exit 0）
2. `upstream-usage-h`（`physlock -h` → `usage: physlock [-dhLlmsv] [-p MSG]`，exit 0）
3. `upstream-invalid-option`（`physlock -Z` → usage，exit 1）

## 二、test_package（消费者验证，不等于上游测试）

| 指标 | 值 |
|------|-----|
| 用例总数 | **9** |
| 通过 / 失败 / 跳过 | **9 / 0 / 0** |
| 其中鸿蒙平台特有（≥1） | **4** |

| # | 用例名称 | 类型 | 结果 |
|---|----------|------|------|
| 1 | `OHOS-01` physlock 可执行文件已安装 | 鸿蒙特有 | PASS |
| 2 | `OHOS-02` ELF 目标架构 AArch64/OHOS PC | 鸿蒙特有 | PASS |
| 3 | `OHOS-03` OHOS musl 解释器 `/lib/ld-musl-aarch64.so.1` | 鸿蒙特有 | PASS |
| 4 | `OHOS-04` 存在 OHOS `.codesign` 签名段 | 鸿蒙特有 | PASS |
| 5 | `CLI-01` `physlock -v` 输出版本 13 | 上游行为 | PASS |
| 6 | `CLI-02` `physlock -h` 输出 usage 且退出 0 | 上游行为 | PASS |
| 7 | `CLI-03` 非法选项输出 usage 且退出非 0 | 上游行为 | PASS |
| 8 | `PKG-01` 渲染后的 man page 已安装 | 打包完整性 | PASS |
| 9 | `PKG-02` man page `VERSION` 占位符已替换 | 打包完整性 | PASS |

> test_package 为消费者验证，**不能替代上游测试统计**（上游确无自动化测试）。

## 三、命令与退出码

```bash
# 1. 真实构建（conan create 内部 build()）
$ conan create archives/p/physlock/13 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd
... Launching test_package ...
PASS OHOS-01 .. PASS PKG-02
physlock/13 test_package: 9/9 passed
# exit 0        （日志：reports/conan-create.log）

# 2. 配方门禁
$ python3 scripts/ohc-run.py conan-verify physlock 13
✅ 配方验证通过: physlock 13   # G1-G4 + L2/L4/L5 全 PASS，exit 0
# 报告：reports/conan-verify-report.md

# 3. 上游样例（staging/包内二进制，安全入口）
$ ./physlock -v   ; echo $?   # physlock 13            -> 0
$ ./physlock -h   ; echo $?   # usage: physlock [...]  -> 0
$ ./physlock -Z   ; echo $?   # usage: physlock [...]  -> 1

# 4. 本地 CI 模拟（W3）
$ python3 scripts/ohc-run.py finish physlock 13 built
# .ci-result.json: exit_code=0  （日志：reports/w3-local-ci.log）
```

## 四、结论

- 上游自动化测试：**无**（0 例）。
- 上游文档化样例：3 例，全部通过。
- 消费者验证（test_package）：9/9 通过，其中鸿蒙特有 4 例。
- 不可测项：真机锁屏 happy-path（需 root/设备），如实记录，未伪装通过。
