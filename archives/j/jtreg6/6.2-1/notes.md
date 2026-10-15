# jtreg6 6.2-1 适配笔记

> 软件：jtreg（OpenJDK JDK Regression Test Harness）6.2+1
> 平台：HarmonyOS PC aarch64（HongMeng Kernel 1.12.0，musl libc）
> 状态：built（真机 conan create + test_package 通过；见 reports/）

## 编译环境
- 构建系统：GNU make（上游 `make/build.sh` 包装脚本）
- JDK：BiShengJDK 17.0.13（`~/bishengjdk17`，配方缺失时经 cmd-pkgs 自动安装）
- 构建依赖：Ant 1.10.8（配方预取缓存）、JT Harness jt6.0-b14 / JCov jcov3.0-b07 / AsmTools 7.0-b09（上游 build.sh 从 GitHub 源码构建）、JUnit 4.13.2、TestNG 7.3.0 + Guice 4.2.3 + JCommander 1.78（Maven 阿里云镜像）
- 编译器：平台无关（纯 Java + javac），运行时 clang 15.0.4 工具链不参与

## 编译步骤

```bash
# 上游标准流程（配方 build() 自动执行）：
export JAVA_HOME=~/bishengjdk17
export JTREG_VERSION_STRING="6.2+1"
bash make/build.sh --jdk "$JAVA_HOME" -- -j2      # 下载依赖 + 构建 jtreg/jtdiff
MAKE_ARGS=quick-test HEADLESS=1 bash make/build.sh --jdk "$JAVA_HOME" --skip-download
# 产物：build/images/jtreg/{bin,lib,doc,legal,release}
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | javac `-Werror` 报 `[path] bad path element`，类路径以 `;` 连接 | `uname -s`=HarmonyOS 未被 `make/Platform.gmk` 识别 → 落入 Windows 分支（`PS=';'`） | 补丁 `0002-make-Platform.gmk.patch`：为 HarmonyOS 增加与 Linux 相同的分支 |
| 2 | javac `-Werror` 失败：`AppletWrapper.java: warning: [removal] Applet ... has been deprecated and marked for removal` | JDK 9+ 的 `-Xlint:all` 包含 `removal` 类别；JDK 17（JEP 398）将 Applet 标记 forRemoval，而上游 6.2 CI 用 JDK 11（不触发）；设备仅有 BiShengJDK 17 | 补丁 `0001-make-Defs.gmk.patch`：`Defs.gmk` 的 javac lint 列表排除 `removal`（`EXTRA_LINT_OPTS` 与现代 JDK 分支的 TOOL_JAVAC 两处） |
| 3 | 设备 `wget: Unknown option 'q'`，依赖下载失败 | OHOS toybox wget 不支持 `-q`（且实测下载挂起） | 配方在 curl 可用时生成 wget→curl shim（`WGET` 环境变量传入） |
| 4 | `raw.githubusercontent.com` 不可达（TestNG LICENSE 下载失败） | 网络限制 | 配方从 GitHub 的 testng 源码 tarball 提取 LICENSE.txt（sha1 钉校验后经 `TESTNG_LICENSE` 传入） |
| 5 | `archive.apache.org` 下载 Ant 被限速 ~20KB/s | 网络限速 | 配方预取 Ant（sha1 钉校验）并缓存到 `~/apache-ant-1.10.8`，经 `ANT` 环境变量传给 build.sh |
| 6 | `git.openjdk.org` 302 重定向链路不稳定 | 重定向到 GitHub 时连接重置 | `CODE_TOOLS_URL_BASE=https://github.com/openjdk`（JT Harness/JCov/AsmTools 官方源在 GitHub） |
| 7 | 设备侧偶发 GitHub SSL EOF（jtharness 源码 zip 下载中断，curl 56） | 传输抖动 | 配方 `build()` 内置 3 次重试（本地实测一次抖动后重试成功） |
| 8 | `make: jobserver mkfifo: ...: Operation not permitted` | HMDFS 不支持 mkfifo，GNU make 4.4 的 `-j2` jobserver 不可用 | 非致命：make 退化调度后构建正常完成（仅提示） |

## 源码修改

- `patches/0001-make-Defs.gmk.patch`（±2 行，portability）：
  `make/Defs.gmk` 中 javac lint 列表排除 `removal` 类别——JDK 17 的
  `-Xlint:all` 会因 `Applet`（JEP 398，forRemoval）产生 warning，
  在上游 `-Werror` 下直接失败；排除后与上游 CI（JDK 11 时代）行为一致。
- `patches/0002-make-Platform.gmk.patch`（+9 行，portability）：
  在 `make/Platform.gmk` 为 `uname -s` = `HarmonyOS` 增加平台分支，
  `OS_NAME=linux`、`OS_ARCH=$(uname -m)`、`OS_VERSION=$(uname -r)`，
  避免落入 Windows 分支的分号类路径分隔符。

## 依赖版本

- BiShengJDK 17.0.13（运行时/构建时 JDK）
- Apache Ant 1.10.8（校验 SHA1 `dbe187ce2963f9df8a67de8aaff3b0a437d06978`）
- JT Harness jt6.0-b14 / JCov jcov3.0-b07 / AsmTools 7.0-b09（上游 build.sh 从 GitHub 源码构建）
- JUnit 4.13.2 / TestNG 7.3.0 / Guice 4.2.3 / JCommander 1.78（Maven Central，阿里云镜像）

## 上游测试（R51 三步法）

1. **清点**：上游自测由 GNU make 目标组织（`test/*.gmk` 的 `*.ok` 目标）；上游 CI
   （.github/workflows/test.yml）先跑 `quick-test`（HEADLESS=1）再跑全量 `test`。
2. **实际运行（HarmonyOS PC 真机）**：
   - `quick-test`（HEADLESS=1）：**6/6 通过**（tidy-docs、Basic.check、i18n×4），由
     `conan create` 在 build() 中执行（CI 可复现）。
   - 全量 `make -k test`（HEADLESS=1）：选中 **184** 个目标，**180 通过 / 4 失败**（97.8%）：
     | 目标 | 结果 | 根因（均为平台/工具语义差异，非 jtreg 功能缺陷） |
     |------|------|--------------------------------------------------|
     | CleanupTests.agentvm.retain | 失败（5 用例本身全 PASS） | 鸿蒙 chmod 只读语义受限，"不可删除文件"可被删除，残留 scratch 目录计数 1 != 5 |
     | ProblemList | 失败 | make 侧平台键（linux-*）与 JVM `os.name=HarmonyOS`/`os.version="HongMeng Kernel 1.12.0"` 视图不一致，OSNAME 系 3 条排除静默失配（generic-all/arch 两条正常生效）→ 期望 passed:1，实测 passed:4 |
     | SkippedExceptionTest.agentvm | 失败 | 设备 toybox grep 不支持 BRE `\+`，summary 精确行断言无法匹配（结果断言 passed:1; failed:2 已匹配，实际结果与期望一致） |
     | SkippedExceptionTest.othervm | 失败 | 同上 |
3. **回填**：见 `reports/test-report.md` 与 PR 正文统计表。

## 验证结果

```bash
# 真机构建（conan create 干净构建 + test_package 消费者测试）
conan create archives/j/jtreg6/6.2-1 -pr:h=ohos-aarch64-device -pr:b=ohos-aarch64-device
sh <pkg>/bin/jtreg -version        # jtreg 6.2+1 / BiShengJDK 17.0.13
# test_package：迷你 JDK 套件（1 通过 + 1 故意失败）
#   Test results: passed: 1; failed: 1（jtreg 正确统计并通过 12 项断言）
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/jtreg`、`bin/jtdiff` | 命令行入口（R38 commands.json 已声明） |
| `lib/jtreg.jar`、`lib/javatest.jar` | 核心 harness |
| `lib/asmtools.jar`、`lib/testng-*.jar` 等 | 上游捆绑依赖 |
| `doc/`、`legal/`、`release`、`LICENSE`、`COPYRIGHT` | 上游镜像完整性 |

## 注意事项

- 运行 jtreg 需要 JDK 17+（`-jdk:` 或 `JAVA_HOME`）；被测试的 JDK 由用户提供。
- 本包为纯 Java 工具，无 .so 产物；Conan settings 四项仅为 CI L0p 门禁完整性保留。
- 平台任务标注 `lang=cpp` 为批量误标：上游为 Java 项目（源文件 584 个，`.java` 占 100%），
  lang-preflight 按实际语言 Java 复核通过（同族先例 jtreg8 与 jakarta-* 均为 Java 适配流程）。

---

**编译结束**: 2026-10-14 18:08
**最终状态**: built
