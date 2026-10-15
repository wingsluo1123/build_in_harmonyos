# jtreg7 7.5.2-1 适配笔记

> 软件：jtreg（OpenJDK JDK Regression Test Harness）7.5.2+1
> 平台：HarmonyOS PC aarch64（HongMeng Kernel 1.12.0，musl libc）
> 状态：built（真机 conan create + test_package 通过；见 reports/）

## 编译环境
- 构建系统：GNU make（上游 `make/build.sh` 包装脚本）
- JDK：BiShengJDK 17.0.13（`~/bishengjdk17`，配方缺失时经 cmd-pkgs 自动安装）
- 构建依赖：Ant 1.10.8（配方预取缓存）、JT Harness jt6.0-b24 / AsmTools 7.0-b09（上游 build.sh 从 GitHub 源码构建）、JUnit platform console standalone 1.11.0、TestNG 7.3.0 + Guice 5.1.0 + JCommander 1.82（Maven 阿里云镜像）
- 编译器：平台无关（纯 Java + javac），运行时 clang 15.0.4 工具链不参与

## 编译步骤

```bash
# 上游标准流程（配方 build() 自动执行）：
export JAVA_HOME=~/bishengjdk17
export JTREG_VERSION_STRING="7.5.2+1"
bash make/build.sh --jdk "$JAVA_HOME" -- -j2      # 下载依赖 + 构建 jtreg/jtdiff
MAKE_ARGS=quick-test HEADLESS=1 bash make/build.sh --jdk "$JAVA_HOME" --skip-download
# 产物：build/images/jtreg/{bin,lib,doc,legal,release}
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | javac `-Werror` 报 `[path] bad path element`，类路径以 `;` 连接 | `uname -s`=HarmonyOS 未被 `make/Platform.gmk` 识别 → 落入 Windows 分支（`PS=';'`） | 补丁 `0001-make-Platform.gmk.patch`：为 HarmonyOS 增加与 Linux 相同的分支。补丁前真机微探针实测 `OS_NAME=windows PS=;`，补丁后 `OS_NAME=linux PS=:` |
| 2 | 设备 `wget: Unknown option 'q'`，依赖下载失败 | OHOS toybox wget 不支持 `-q`（且实测下载挂起） | 配方在 curl 可用时生成 wget→curl shim（`WGET` 环境变量传入） |
| 3 | `raw.githubusercontent.com` 不可达（TestNG LICENSE 下载失败） | 网络限制 | 配方从 GitHub 的 testng 源码 tarball 提取 LICENSE.txt（sha1 钉校验后经 `TESTNG_LICENSE` 传入） |
| 4 | `archive.apache.org` 下载 Ant 被限速 ~20KB/s | 网络限速 | 配方预取 Ant（sha1 钉校验）并缓存到 `~/apache-ant-1.10.8`，经 `ANT` 环境变量传给 build.sh |
| 5 | `git.openjdk.org` 302 重定向链路不稳定 | 重定向到 GitHub 时连接重置 | `CODE_TOOLS_URL_BASE=https://github.com/openjdk`（JT Harness/AsmTools 官方源在 GitHub） |
| 6 | 设备侧偶发 GitHub SSL/超时（jtharness 源码 zip 下载中断） | 传输抖动 | 配方 `build()` 内置 3 次重试；设备网络实测多次一过性重置后重试成功 |
| 7 | `make: jobserver mkfifo: ...: Operation not permitted`（偶发） | HMDFS 不支持 mkfifo，GNU make 的 `-j2` jobserver 不可用 | 非致命：make 退化调度后构建正常完成（仅提示） |
| 8 | 本地 conan-verify G2 注入的 ghfast.top 镜像已失效 | `conan_verify.py` 对 github.com URL 的 E017 预防注入；ghfast.top 当前不可达（实测连接超时） | 本地验证期间 conandata 源临时指向 **codeload.github.com**（GitHub 官方归档同字节源，sha256 一致 `ce0c9971…`）；提交版 conandata 为官方 GitHub URL（已核验还原） |

## 源码修改

- `patches/0001-make-Platform.gmk.patch`（唯一补丁，+9 行，portability）：
  在 `make/Platform.gmk` 为 `uname -s` = `HarmonyOS` 增加平台分支，
  `OS_NAME=linux`、`OS_ARCH=$(uname -m)`、`OS_VERSION=$(uname -r)`，
  避免落入 Windows 分支的分号类路径分隔符。

> 版本差异实证（与同族 6.2 对比）：jtreg 6.2 需要额外补丁在 `make/Defs.gmk`
> 排除 `removal` lint 类别（JDK 17 将 Applet 标记 forRemoval，`-Xlint:all -Werror`
> 直接失败）；**7.5.2 的 Defs.gmk 使用 `--release 8/11` 目标版本编译**，
> 旧 API 视图下不产生 removal 警告，无需该补丁（上游 CI 同用 JDK 21 全量构建验证）。

## 依赖版本

- BiShengJDK 17.0.13（运行时/构建时 JDK）
- Apache Ant 1.10.8（校验 SHA1 `dbe187ce2963f9df8a67de8aaff3b0a437d06978`）
- JT Harness jt6.0-b24 / AsmTools 7.0-b09（上游 build.sh 从 GitHub 源码构建，sha1 校验）
- JUnit platform console standalone 1.11.0 / TestNG 7.3.0 / Guice 5.1.0 / JCommander 1.82（Maven Central，阿里云镜像）

## 上游测试（R51 三步法）

1. **清点**：上游自测由 GNU make 目标组织（`test/*.gmk` 的 `*.ok` 目标）；
   上游 CI（.github/workflows/test.yml）先跑 `quick-test`（HEADLESS=1）再跑全量 `test`。
2. **实际运行（HarmonyOS PC 真机）**：
   - `quick-test`（HEADLESS=1）：make 汇总 **All (10) selected tests completed successfully**
     （checkJavaOSVersion + BUILDTESTDIR + INITIAL_TESTS：tidy-docs、Basic.check/othervm/agentvm、
     i18n×3、JUnitTrace.agentvm），由 `conan create` 在 build() 中执行（CI 可复现）。
   - 全量 `make -k test`（HEADLESS=1）：选中 **257** 个目标，**253 通过 / 4 失败**（98.4%），无挂起：
     | 目标 | 结果 | 根因（均为平台/工具语义差异，非 jtreg 功能缺陷） |
     |------|------|--------------------------------------------------|
     | CleanupTests.agentvm.retain | 失败（5 用例本身全 PASS，jt.log: `Test results: passed: 5`） | 鸿蒙 chmod 只读语义受限，"不可删除文件"可被删除，jtreg 复用 scratch 目录（实测 1 个）≠ 期望 5 个 |
     | ProblemList | 失败 | JVM `os.version` 含空格（"HongMeng Kernel 1.12.0"），OSNAME-REV 排除选择器失配 → `passed: 2; excluded: 4`（期望 `passed: 1`） |
     | SkippedExceptionTest.agentvm | 失败 | 设备 toybox grep 不支持 BRE `\+`，summary 精确行断言无法匹配（实际结果 `passed: 1; failed: 2; skipped: 1` 与期望一致） |
     | SkippedExceptionTest.othervm | 失败 | 同上 |
3. **回填**：`quick-test` 由 `conan create` 在 build() 中执行（CI 可复现）；
   全量 257 目标统计为真机实测（`make -k test`，HEADLESS=1）。

## 验证结果

```bash
# 真机构建（conan create 干净构建 + test_package 消费者测试）
conan create archives/j/jtreg7/7.5.2-1 -pr:h=ohos-aarch64-device -pr:b=ohos-aarch64-device
sh <pkg>/bin/jtreg -version        # jtreg 7.5.2+1 / BiShengJDK 17.0.13
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
- 平台任务标注 `lang=cpp` 为批量误标：上游为 Java 项目（源文件 640 个，`.java` 占 100%），
  lang-preflight 按实际语言 Java 复核通过（同族先例 jtreg6/jtreg8 与 jakarta-* 均为 Java 适配流程）。

**编译结束**: 2026-10-14 17:19
**最终状态**: built
