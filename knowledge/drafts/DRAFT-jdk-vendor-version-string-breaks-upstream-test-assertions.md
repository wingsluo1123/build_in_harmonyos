# 上游测试断言写死 JDK 厂商版本串/平台名时 OpenJDK 系 JDK（BiSheng）假失败：厂商中性扩展匹配补丁修复 + Assume 平台守卫跳过按设计内辨析（openjdk version / os.name=HarmonyOS，zt-exec 1.12 案例）

> 草稿（DRAFT）— 与 `.kv` 同 stem 配对，字段对齐 `knowledge/graph/_template.kv`。
> 修订自 DRAFT-14403-junit-oracle-version-string-vendor-assumption：按 Curator
> 审计去库名-版本化命名、补 affected_scope/fallback_*/forbid_* 全字段、
> verification 改自包含探针、principles 挂钩、related 改挂实存图谱条目。

## 问题（规则陈述）

两类 JDK 厂商假设会让上游测试在 OpenJDK 系 JDK 上**假失败**：

1. **版本串**：Oracle JDK `java -version` 首行是 `java version "1.8.0_x"`；
   OpenJDK 系（BiSheng/Temurin 等）是 `openjdk version "17.x"`。测试若以
   字面 `java version` 作触发条件（如 listener 抛异常）或输出断言，条件永假。
2. **平台名**：bisheng JDK 在 OHOS 上 `os.name = HarmonyOS`（非 Linux/Mac/
   Windows），`SystemUtils.IS_OS_LINUX` 等分支与 JUnit `Assume` 守卫的走向
   与上游 CI 不同。

## 案例事实（zt-exec 1.12，run3）

- `Tests run: 96, Failures: 2, Errors: 0, Skipped: 1` → BUILD FAILURE。
- 2 失败：`ProcessListenerThrowTest.testJavaVersion/testJavaVersionWithTimeout`
  —— listener 期望输出含 `java version` 时抛 InvalidOutputException；
  BiSheng 输出 `openjdk version` → 预期异常永不触发
  （`Expected exception: ...InvalidOutputException` AssertionError）。
- 1 skip：`InputRedirectTest` —— `SystemUtils.IS_OS_LINUX` 为假触发上游
  `Assume.assumeTrue("Unsupported OS ...")`，属**设计内跳过**（上游自己
  的平台守卫），不是缺陷。

## 自包含验证探针（离开 run 可复现）

```sh
java -version 2>&1 | head -1
# 期望（BiSheng 17.0.13，需 PATH 含 JAVA_HOME/bin）: openjdk version "17.0.13" ...
# 对照（Oracle JDK 8）: java version "1.8.0_x"
```

## 可复用修复范式

最小**厂商中性扩展匹配**补丁（不改测试意图，任何厂商下语义一致）：

```diff
-      if (result.getOutput().getString().contains("java version")) {
+      if (result.getOutput().getString().contains("java version")
+          || result.getOutput().getString().contains("openjdk version")) {
```

要点：
1. 补丁以 `patch_type: portability` 进 conandata，可审阅、可重放（P-PATCH-001）。
2. 识别特征：surefire 报 `Expected exception: X` 的 AssertionError，而被测
   进程真实输出里是 `openjdk version`。
3. Assume 守卫类 skip 在交付报告里区分为"设计内跳过"（记录 1 skipped 及
   原因），不得计入失败，也不得借机 NOT_RUN。
4. 次选（仅当扩展匹配不可行）：surefire excludes（`-Dtest=!XxxTest`）或
   @Ignore，逐条记录排除理由与上游用例数差值——弱化验证，审慎使用。

## 禁止

- 对 `src/test/**` 就地 sed/删除而不落可审阅 patch（重新解包即丢失，测试
  静默变弱）。

## principles

- **P-PATCH-001（principles.kv id P003）**：修改必须保存为 .patch——上游测试
  的任何修订以 portability patch 呈现并记录理由。

## 关系

- 同族：**E184**（Java 构建工具链缺失与自举）。
- similar_to：**E083**（BiSheng JDK 厂商特有行为）、**E084**（Java 无
  ant/maven 手工构建）。
- 姊妹稿：`DRAFT-java-user-home-unset-scatters-tool-state-dirs`（同 run 另一
  独立 FAIL→PASS 面）。
- 原稿：DRAFT-14403-junit-oracle-version-string-vendor-assumption（本稿去
  版本化修订版）。

## 适用面与反例

- 适用：所有在 OpenJDK 系 JDK 上跑 Oracle 主导期（2013-2021）上游测试的
  Java 工程；凡断言/脚本按版本串前缀或 os.name 分支的用例均受影响。
- 反例：上游测试本身用 `ManagementFactory.getRuntimeMXBean().getVmVendor()`
  或正则 `.* version "` 等厂商中性写法的，不命中；Oracle JDK 上重放本探针
  输出 `java version`，说明问题不存在于该环境。

## 证据（run 内）

- run3 FAIL：`runs/zt-exec-1.12/logs/ci-run3.log`（surefire 96/2/1 明细与
  两处 AssertionError 栈）。
- run4 起 PASS：`runs/zt-exec-1.12/logs/ci-run4.log` L891（96 run / 0 fail /
  1 skipped）+ BUILD SUCCESS；run6 为最终候选树复验。
