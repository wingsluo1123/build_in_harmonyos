# DRAFT：只读 meson 的 TAP testlog 统计上游用例，会把「被 SIGABRT 中止的 target」报成 100% 通过

> Draft: `DRAFT-LIBGWEATHER4-444-MESON-TAP-ABORT-UNDERREPORT`
> Stem: `libgweather4-4.4.4-meson-tap-aborted-target-underreport` — pairs with the same-stem `.kv`

## 错误特征

同一跑，两个判据自相矛盾（2026-10-08 22:44，设备 3QC0124C11000071，
libgweather4 4.4.4，conan `build()` 内执行上游 `meson test`）：

meson 控制台（stdout）：

```
▶ 2/5 /weather/named-timezones-deserialized - GWeather:ERROR:../libgweather/tests/timezones.c:122:test_named_timezones_deserialized: 'tz' should not be NULL FAIL
2/5 libgweather:timezones                   ERROR            0.18s   killed by signal 6 SIGABRT

Summary of Failures:

2/5 libgweather:timezones                   ERROR            0.18s   killed by signal 6 SIGABRT

Ok:                4
Fail:              1
```

同一跑的 `meson-logs/testlog.txt`（TAP）：只有 11 行结果，**10 个 ok、1 个 skip、
0 个 not ok**——被中止的 target 里，`named-timezones-deserialized` 在断言处
`abort()`，`timezones` 压根没轮到执行，两个用例一行都没写。

于是**只读 testlog 的配方**打印出：

```
libgweather4: upstream test summary: 10/10 executed cases passed, 1 skipped, 0 failed (0 attributed), 11 meson test entries
```

字面上 100% 通过，而 meson 自己给这一跑的判定是 `Fail: 1`、退出码 1。
更糟的是：非零退出码如果被 `try/except ConanException` 接住后没人再看，
失败就被**整段吞掉**，构建照常继续、门禁照常绿。

## 根因

1. **TAP 行由测试程序自己打印**。GLib 的 `g_assert_*` 失败会立刻 `abort()`，
   进程当场消失：先前的用例留下 `ok N - ...`，真正失败的用例来不及打
   `not ok`，后面的用例永远不会有输出。**「TAP 里没有 not ok」≠「没有失败」。**
2. **meson 的判据是子进程退出状态**，不是 TAP 文本。target 被信号杀死即计入
   `Fail`，并把 `Summary of Failures:` / `Ok:` / `Fail:` 打到**控制台**
   （不写进 `testlog.txt`）。不捕获 stdout 就拿不到 target 级判据。
3. **两个源各缺一半**：testlog 有 case 粒度但会被中止截断；stdout 有 target
   判据但没有 case 明细。任吃一个都会在「失败以中止形式出现」时数错。

第三份对账证据来自上游源码里的注册点（不依赖任何运行输出）：

```
$ grep -c g_test_add_func libgweather/tests/*.c
test_libgweather.c:7   duplicates.c:2   timezones.c:3   metar.c:1   → 13
$ grep -cE '^(ok|not ok)' meson-logs/testlog.txt                    → 11
差 2 = /weather/named-timezones-deserialized、/weather/timezones（被中止的 target）
```

## 解决方案

conan 配方里（`build()` 调用）：

```python
stdout_path = os.path.join(self.build_folder, "meson-logs", "upstream_test_stdout.txt")
cmd = (f'meson test -C "{self.build_folder}" --print-errorlogs '
       f'--no-suite=style --timeout-multiplier 4 '
       f'> "{stdout_path}" 2>&1; rc=$?; cat "{stdout_path}"; exit $rc')
run_error = None
try:
    self.run(cmd, env="conanbuild")     # self.run 走 shell，重定向可用
except ConanException as err:
    run_error = err                     # 接住 ≠ 放行，后面必须判
```

然后**双源对账 + 注册点兜底**：

| 判据 | 来源 | 作用 |
|---|---|---|
| target 级 | stdout 的 `Summary of Failures:` + `Ok:`/`Fail:` | 唯一权威；解析不到就 `raise`，不许「拿不到判据就算过」 |
| case 级 | `meson-logs/testlog.txt` 的 `ok/not ok` | 明细与通过率 |
| 缺口 | 上游 `g_test_add_func` 注册点 − TAP 已报 | 把被中止、没进 TAP 的用例**逐条点名** |

归因（平台数据/网络缺口导致的失败）必须是 **target 名 + 日志签名**双重校验，
签名不在日志里就当移植缺陷抛错，否则归因表会把真回归一起放行：

```python
_ATTRIBITED_UPSTREAM_TARGETS = {
    "timezones": ("platform data: OHOS 无 /usr/share/zoneinfo 文件树 …",
                  ("timezones.c", "should not be NULL", "invalid timezone")),
}
# 命中 → self.output.warning 打 cause 原文进 CI 日志，构建继续
# 未命中/签名缺失 → raise ConanException("… port defect: …")
```

修复后同一批设备实跑的输出（2026-10-08 23:35，gate3 rc=0 / Pass rate 100%）：

```
libgweather4: upstream meson summary (measured): Ok=4 Fail=1 targets; TAP cases: 10 ok, 1 skip, 0 fail; registered g_test cases=13, reported by TAP=11, not reported (target aborted)=2
libgweather4: attributed upstream target failure libgweather:timezones
libgweather4: upstream test result: 4/5 meson targets OK; 13 registered g_test cases executed; 10 passed, 1 skipped, 2 failed with attribution; … counts stand as measured
```

## 验证命令

```bash
BF=<builddir>
# 1) 跑并同时拿到 stdout 与退出码
meson test -C "$BF" --print-errorlogs --no-suite=style > "$BF/meson-logs/stdout.txt" 2>&1
echo "exit=$?"
# 2) target 级判据（控制台汇总，不在 testlog 里）
grep -E "^(Ok|Fail):" "$BF/meson-logs/stdout.txt"
sed -n '/Summary of Failures:/,$p' "$BF/meson-logs/stdout.txt"
# 3) case 级判据
grep -cE '^ok '     "$BF/meson-logs/testlog.txt"
grep -cE '^not ok ' "$BF/meson-logs/testlog.txt"
# 4) 注册点对账：registered − reported = 被中止没上报的用例
grep -ch g_test_add_func libgweather/tests/*.c | paste -sd+ | bc
# 5) 负向复现：故意让一个 target 断言失败（g_assert_nonnull(NULL)），
#    确认 testlog 里没有 not ok、但 stdout 有 Fail: 1 —— 只吃 testlog 就会误判全过
```

## 禁止策略

- ❌ 只统计 `meson-logs/testlog.txt` 的 `not ok` 数就宣布「上游 0 失败 / 100% 通过」
- ❌ 接住 `self.run()` 抛出的非零退出码后**不再判**——那是把失败整段吞掉
- ❌ 归因表按「用例名前缀」或「target 名」裸放行、不校验日志签名（真回归会被掩盖）
- ❌ 在没跑过任何一次真实构建的情况下，把通过率写进 PR 描述 / MANIFEST（R51 少报即 FAIL）
- ❌ 用 `meson test` 退出码 0 当作「全部用例都执行了」——退出码只说「没有失败」

## 关联条目

- 互补：`DRAFT-libgmobile-0.7.2-meson-not-installed-is-not-skipped-and-exit-code-is-not-coverage`
  （退出码 0 不代表覆盖率 / `not_installed` 不是「不执行」）
- 同类「统计口径会数错」：`DRAFT-libnm-1.52.1-upstream-test-harness-false-negatives`
- 本条由 libgweather4 4.4.4 移植实测产出（PR #13996，设备 3QC0124C11000071，
  原始日志 `gwbuild_full2.log`（误报现场）/ `gwbuild_full3.log`（修复后））
