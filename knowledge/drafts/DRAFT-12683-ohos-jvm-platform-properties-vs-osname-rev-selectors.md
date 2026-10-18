# DRAFT-12683-ohos-jvm-platform-properties-vs-osname-rev-selectors

> 草稿（DRAFT）—— 来源：jtreg 8.3+1 适配 HarmonyOS PC（PR #14710 / 任务 12683）真机验证
> 与 `.kv` 同 stem 配套；字段见 `knowledge/drafts/DRAFT-12683-ohos-jvm-platform-properties-vs-osname-rev-selectors.kv`

## 症状

jtreg（JDK 回归测试框架）在 HarmonyOS PC 真机跑自测 `make test` 时，`ProblemList`
测试目标失败，但其失败形态是**静默的平台选择器语义差异**，不是崩溃或断言报错：

```
# 期望（Linux 上游 CI）：ProblemList 第二次运行只跑 ExcludeNever.java
Test results: passed: 1
# 真机实测：
Test results: passed: 2; excluded: 4
（report/text/summary.txt）
ExcludeNever.java      Passed. Execution successful
ExcludeOsNameRev.java  Passed. Execution successful   ← 本应被 OSNAME-REV 条目排除
```

同一个 JVM 工具（Gradle）在 OHOS 上则是**显式失败**形态：

```
java.lang.ExceptionInInitializerError: ... Gradle 的 OperatingSystem 类不识别 "HarmonyOS"
（archives/g/gradle/8.12 包先例：wrapper 注入 -Dos.name=Linux 规避）
```

## 根因

系统有两个“平台视图”，Linux 生态默认二者一致，HarmonyOS 上不一致：

| 视图 | 取值 | 使用者 |
|------|------|--------|
| 内核视图 | `uname -s` = `HarmonyOS`、`uname -r` = `HongMeng Kernel 1.12.0` | 构建脚本（config.guess/Makefile/CMake） |
| **JVM 属性视图** | `os.name` = `HarmonyOS`、`os.version` = `HongMeng Kernel 1.12.0`（**含空格、非 x.y.z**）、`os.arch` = `aarch64` | Java 工具/测试运行期 |

Linux 生态约定 JVM 平台属性是“内核-发行版”视图（`os.name=linux`、`os.version=5.15.x` 无空格），
因此工具普遍按 `osname-arch`、`osname-版本` 约定**生成并匹配平台选择器**。在 HarmonyOS 上：

1. **生成侧**把 `os.version` 去空白得 `harmonyos-hongmengkernel1.12.0`；**匹配侧**语义不同 →
   选择/排除条目静默失效。jtreg/JavaTest 的 ProblemList（`OSNAME-REV` 编码）正是这种机制：
   排除条目没生效 → 多跑 1 个用例且全程无任何告警。
2. **按 `os.name` 枚举分支**的工具直接抛错（Gradle `OperatingSystem` → `ExceptionInInitializerError`）。

## 复现与核验

```bash
# 1) 属性视图
java -XshowSettings:properties -version 2>&1 | grep -E 'os\.(name|arch|version)'
#  os.name = HarmonyOS
#  os.arch = aarch64
#  os.version = HongMeng Kernel 1.12.0     ← 含空格、非语义版本号

# 2) jtreg 自测（真机，HEADLESS=1）
#    ProblemList 目标：passed:2; excluded:4（期望 passed:1）
#    证据：archives/j/jtreg8/8.3-1/reports/test-report.md、notes.md（PR #14710）

# 3) 生成 vs 匹配对照（jtreg 自测产物）
cat <workdir>/ProblemList/2/ProblemList.txt   # harmonyos-hongmengkernel1.12.0
```

## 适配模式（三类，按需选用）

1. **启动选项规范化**（工具必须识别 linux 时）：`JAVA_TOOL_OPTIONS` 注入 `-Dos.name=Linux`；
   `JAVA_TOOL_OPTIONS` 会被所有 JVM 进程（含 fork/daemon）继承，优于只改单一入口
   （Gradle 8.12 包 wrapper 实测形态）。
2. **选择器精度**：生成/匹配 `OSNAME-REV` 时不要假设 `os.version` 无空格/为语义版本；
   使用完整字符串、通配/前缀分组，或改按 `os.name` 分组。
3. **测试侧归因纪律**：把“多跑/漏跑用例”归因为平台属性视图差异并记录（不修改上游断言凑绿），
   在测试报告中如实注明（R51）。

## 与现有知识的边界

- `E007/E160/E140`、`DRAFT-10767`、`DRAFT-12718`（kamailio）等覆盖的是**构建期** `uname -s`/
  config.guess/CMake 平台识别；本条是 **JVM 运行期属性面**，构建脚本之外的工具/测试同样命中。
- `DRAFT-gradle-launcher-toybox-xargs-quote-strip` 仅在说明中一句带过 `-Dos.name=Linux`；
  本条给出完整机制（生成/匹配两侧、空格、静默失效）与 JavaTest ProblemList 第一手案例。
- 与 `E083`（JNI 运行期）无关。

## 验证证据（本 PR）

- 真机全量自测 271 目标：266 通过 / 4 失败 / 1 挂起；其中 ProblemList 即本条目标，
  根因由生成文件 + summary 对照坐实。
- `quick-test` 9/9 与 conan-verify G0–G4 PASS 表明该差异不影响 jtreg 功能，只影响
  平台选择器语义与通过率口径。
