# draft-jtreg6-6.2.1-jdk17-javac-removal-lint-werror-legacy-java-builds

## 症状

jtreg 6.2+1（2022-2023 年代码基线的纯 Java 项目）在 **JDK 17** 上以
`-Xlint:all -Werror` 编译时失败：

```
../src/share/classes/com/sun/javatest/regtest/agent/AppletWrapper.java:138: warning: [removal] Applet in java.applet has been deprecated and marked for removal
            Applet applet = app.getApplet();
            ^
...（共 9 处 [removal] warning，全部来自 AppletWrapper.java 的 java.applet 用法）
error: warnings found and -Werror specified
1 error
9 warnings
```

失败目标：`classes.com.sun.javatest.regtest-othervm.ok`（make/jtreg.gmk:42，
`javac -Xlint:all,-options,-deprecation,-rawtypes,-unchecked -Werror`）。

## 根因

1. JDK 9 引入 `removal` lint 类别（`@Deprecated(forRemoval=true)`），并包含在
   `-Xlint:all` 中；JDK 17（JEP 398）把 `java.applet.Applet` 标记为 forRemoval。
2. jtreg 6.2 的 makefile 只排除 `deprecation/rawtypes/unchecked`，未排除 `removal`；
   上游 CI（.github/workflows/test.yml）用 **JDK 11** 构建（`JAVA_HOME_11_X64`），
   该版本 Applet 尚未 forRemoval，因此上游从未暴露。
3. HarmonyOS PC 侧仅有 BiShengJDK 17（`~/bishengjdk17`），Java 构建必须用 JDK 17，
   于是 `-Werror` 把新的 removal 警告升级为错误。
4. 属一类问题：任何在 JDK 17+ 上构建、且编译参数含 `-Xlint:all -Werror` 的
   旧 Java 代码基线（JDK 11 时代及更早），都可能因 `removal` 类别新增警告而
   直接构建失败——不限于 Applet，任何新标记 forRemoval 的 API 同理。

## 修复

在构建脚本的 javac lint 列表**排除 removal**（本 PR 补丁 `0001-make-Defs.gmk.patch`）：

```diff
 else
-    EXTRA_LINT_OPTS = -rawtypes,-unchecked
+    EXTRA_LINT_OPTS = -rawtypes,-unchecked,-removal
     REGTEST_TOOL_PATCH_JAVA_BASE_OPTIONS = --patch-module java.base=$(JAVADIR)
 endif
@@
 REGTEST_TOOL_JAVAC_OPTIONS = \
-	$(TOOL_JAVAC_SOURCE_TARGET) $(JDK8_BOOTCLASSPATH) -Xlint:all,-options,-deprecation -Werror
+	$(TOOL_JAVAC_SOURCE_TARGET) $(JDK8_BOOTCLASSPATH) -Xlint:all,-options,-deprecation,-removal -Werror
```

替代方案（按场景选择）：
- 用 `--release 8/11` 针对旧 API 编译（需构建系统支持，且不能用到新 API）；
- 钉回 JDK 11 构建（HarmonyOS 生态无该工具链时不可行）；
- 不推荐逐条改上游源码/加 `@SuppressWarnings("removal")`（污染面大、上游不友好）。

## 验证

- jtreg 6.2+1 @ BiShengJDK 17.0.13（HarmonyOS PC aarch64）：
  补丁前 `conan`/`make` 构建在 othervm classes 目标失败（上引日志）；
  补丁后 clean build 成功，`jtreg -version` 报 `jtreg 6.2+1`，
  上游 `quick-test`（HEADLESS=1）6/6 通过，全量自测统计见
  `archives/j/jtreg6/6.2-1/reports/test-report.md`。
- 旁证（代码阅读）：同文件另有以 `javac -version | grep '[8]'` 判定 JDK8 的
  启发式（`SUPPORT_OLD_SOURCE_TARGET`），本例 JDK 17 走现代分支正常；跨大版本
  嗅探的同类脆弱点值得一并复核。

## 查重边界

- `DRAFT-12611-jdk17-patch-build-plugin-compat`（bundle 插件 CME + javadoc
  doclint）与 `DRAFT-12609-jakarta-cdi-api-ohos-device-java-maven-toolchain`
  是 Maven 插件/真机通道面；本条是 **javac 编译器 lint 语义面**（-Xlint:all
  新增类别 × -Werror），触发在无 Maven 的 make/javac 构建链，互不覆盖。
- `E084`（JNA manual-java-native-build）讲缺 ant/maven 时手工构建，不涉及 lint。
