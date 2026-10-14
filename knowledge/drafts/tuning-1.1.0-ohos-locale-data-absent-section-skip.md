# OHOS locale 数据缺失：`std::locale("es_ES")` 抛异常，上游 locale 相关 SECTION 按设计跳过

> Draft: `DRAFT-OHOS-LOCALE-DATA-ABSENT-UPSTREAM-SECTION-SKIP`
> Stem: `tuning-1.1.0-ohos-locale-data-absent-section-skip` — 与同 stem 的 `.kv` 配套

## 基本信息

- **ID**: DRAFT-OHOS-LOCALE-DATA-ABSENT-UPSTREAM-SECTION-SKIP
- **严重度**: 3
- **类别**: locale|ohos-platform|runtime-environment
- **触发工具**: clang|libc++
- **阶段**: runtime|test

## 实测（OHOS aarch64，clang 15 + libc++，2026-10-04）

```
locale 'es_ES       ' -> THROW (collate_byname<char>::collate_byname failed to construct for es_ES)
locale 'fr_FR       ' -> THROW (collate_byname<char>::collate_byname failed to construct for fr_FR)
locale 'zh_CN       ' -> OK (zh_CN)
locale 'en_US.UTF-8 ' -> OK (en_US.UTF-8)
locale 'C           ' -> OK (C)
locale '<empty>     ' -> OK ()
locale 'es_ES.UTF-8' -> THROW (collate_byname<char>::collate_byname failed to construct for es_ES.UTF-8)
```

目标机只有 `zh_CN` / `en_US.UTF-8` / `C`（+ 空串→C）。宿主 `LANG=en_US.UTF-8`。

## 对上游测试的影响（tuning-library）

上游 `run-all-tests` 会以 `LANG=es_ES / fr_FR / zh_CN / 空` 各跑一遍。实测 5 次全部
`All tests passed (242371 assertions in 18 test cases)`：

- `LANG=es_ES` / `fr_FR` / 空 → `main()` 里 `std::locale::global(std::locale(getenv("LANG")))` 抛异常落到
  `catch` 分支（不打印 “Setting LOCALE …”）；
- SECTION `Internal Constraints between Measures / Test All Constraints SCL and KBM in Spain`
  自身 `try { std::locale("es_ES"); } catch { spainAvailable = false; }`（上游
  `tests/alltests.cpp:227-240`）→ **按上游设计跳过**，打印
  `es_ES locale not availale on this machine; skpping test`。

结果：18/18 TEST_CASE 通过、0 失败；62 个 SECTION 中 **61 个执行、1 个跳过**。
这是**平台环境事实**，不是用例失败，也**不是漏测**（该测试数据本身可执行，只是 locale 数据不存在）。

## 报告口径（避免下次误判）

| 口径 | 含义 | tuning 实测 |
|---|---|---|
| TEST_CASE 级 skipped | Catch2 summary 里计入 skipped 的用例 | 0 |
| SECTION 按设计跳过 | 上游自带 try/catch + 环境探测 | 1（Spain locale section） |
| 路径未覆盖 | 依赖 es_ES/fr_FR 数据的断言根本没跑到 | 仅上面那 1 个 SECTION |

**不要把 61 当“漏测 1 个用例”，也不要把 SECTION 跳过写成用例跳过。**

## 处置原则

1. 先跑探针程序列出目标机真实可用 locale，写进测试报告；
2. **不要**为“全绿”删改上游 locale 用例，也**不要**伪造 locale 数据；
3. 要真正覆盖 es_ES 分支，只能补目标机 locale 数据（镜像能力，非配方可解决），否则如实标注未覆盖。

## 证据

- `archives/t/tuning/1.1.0/reports/upstream-test-logs/05_locale_probe.log`
- `archives/t/tuning/1.1.0/reports/upstream-test-logs/06_spain_section_check.log`
- `archives/t/tuning/1.1.0/reports/upstream-test-logs/04_lang_matrix.log`
- `archives/t/tuning/1.1.0/reports/upstream-test-logs/upstream_junit.xml`（61 条 section 路径）
