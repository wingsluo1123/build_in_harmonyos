# Catch2 v2 不支持 `-r <reporter>::<file>`：per-case XML 要用 `-r junit -o <file>`

> Draft: `DRAFT-CATCH2-V2-REPORTER-COLON-COLON-UNSUPPORTED`
> Stem: `tuning-1.1.0-catch2v2-reporter-colon-colon-unsupported` — 与同 stem 的 `.kv` 配套

## 基本信息

- **ID**: DRAFT-CATCH2-V2-REPORTER-COLON-COLON-UNSUPPORTED
- **严重度**: 3
- **类别**: test-framework|cli-usage
- **触发工具**: conan|clang|catch2
- **阶段**: test|reporting

## 现象

在 Catch2 v2.9.2（tuning-library 源码包内置 `libs/catch2/catch2.hpp`）上按 v3 习惯写：

```
$ ./tuning-library-tests -r junit::upstream_junit.xml
Error(s) in input:
  Unrecognized reporter, 'junit::upstream_junit.xml'. Check available with --list-reporters
Run with -? for usage
rc=255
```

`::` 被整体当成 reporter 名。v2 的 `-r` 只接受 reporter 名，输出文件是独立的 `-o`。

## 可用 reporter（实测 `--list-reporters`）

```
compact:  Reports test results on a single line, suitable for IDEs
console:  Reports test results as plain lines of text
junit:    Reports test results in an XML format that looks like Ant's junitreport target
xml:      Reports test results as an XML document
```

## 正确用法

```bash
./tuning-library-tests -r junit -o upstream_junit.xml          # rc=0，XML 落盘（7694 B）
./tuning-library-tests --list-tests                            # 末尾 “18 test cases” 才是 TEST_CASE 级口径
./tuning-library-tests -r compact                              # 控制台摘要：All tests passed (242371 assertions in 18 test cases)
```

## 计数口径提醒

junit reporter 在 v2 里按 **SECTION 路径**产出 `<testcase>`：tuning 实测 61 条
（= 61 个被执行 section，另有 1 个 section 因 OHOS 缺 es_ES locale 按上游设计跳过）。
**TEST_CASE 级总数**以 `--list-tests` 末尾的 `N test cases` 为准（此处 18），
不要把 61 当作用例总数。

## 证据

- `archives/t/tuning/1.1.0/reports/upstream-test-logs/02_reporters.log`（首轮报错原文 + reporter 列表）
- `archives/t/tuning/1.1.0/reports/upstream-test-logs/upstream_junit.xml`
- `archives/t/tuning/1.1.0/reports/upstream-test-logs/07_junit_names.log`（61 条 section 路径清单）
