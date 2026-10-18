# jtreg8 8.3-1 适配笔记

> 软件：jtreg（OpenJDK JDK Regression Test Harness）8.3+1
> 平台：HarmonyOS PC aarch64（HongMeng Kernel 1.12.0，musl libc）
> 状态：built（真机 conan create + test_package 通过；见 reports/）

## 编译环境
- 构建系统：GNU make（上游 `make/build.sh` 包装脚本）
- JDK：BiShengJDK 17.0.13（`~/bishengjdk17`，配方缺失时经 cmd-pkgs 自动安装）
- 构建依赖：Ant 1.10.15（配方预取缓存）、JT Harness jt6.0-b24、AsmTools 9.1-b01、JUnit 1.14.2、TestNG 7.3.0 + Guice 5.1.0 + JCommander 1.82（上游 build.sh 下载并校验）
- 编译器：平台无关（纯 Java + javac），运行时 clang 15.0.4 工具链不参与

## 编译步骤

```bash
# 上游标准流程（配方 build() 自动执行）：
export JAVA_HOME=~/bishengjdk17
export JTREG_VERSION_STRING="8.3+1"
bash make/build.sh --jdk "$JAVA_HOME" -- -j2      # 下载依赖 + 构建 jtreg/jtdiff
bash build/make.sh quick-test                      # 上游初始自测（HEADLESS=1）
# 产物：build/images/jtreg/{bin,lib,doc,legal,release}
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | javac `-Werror` 报 `[path] bad path element`，类路径以 `;` 连接 | `uname -s`=HarmonyOS 未被 `make/Platform.gmk` 识别 → 落入 Windows 分支（`PS=';'`） | 补丁 `0001-make-Platform.gmk.patch`：为 HarmonyOS 增加与 Linux 相同的分支 |
| 2 | 设备 `wget: Unknown option 'q'`，Ant/JUnit 等下载失败 | OHOS toybox wget 不支持 `-q`（且实测下载挂起） | 配方在 curl 可用时生成 wget→curl shim（`WGET` 环境变量传入） |
| 3 | `raw.githubusercontent.com` 不可达（TestNG LICENSE 下载失败） | GFW/网络限制 | 配方从 GitHub 的 testng 源码 tarball 提取 LICENSE.txt（sha1 钉校验后经 `TESTNG_LICENSE` 传入） |
| 4 | `archive.apache.org` 下载 Ant 被限速 ~20KB/s | 网络限速 | 配方预取 Ant（sha1 钉校验）并缓存到 `~/apache-ant-1.10.15`，经 `ANT` 环境变量传给 build.sh |
| 5 | `git.openjdk.org` 302 重定向链路不稳定 | 重定向到 GitHub 时连接重置 | `CODE_TOOLS_URL_BASE=https://github.com/openjdk`（JT Harness/AsmTools 官方源仍在 GitHub） |
| 6 | ohc-run.py 把源码根误判为 `make/`（嵌套提升） | jtreg 根目录无 configure/CMakeLists/Makefile 标记，工具在子目录找到 `make/Makefile` | 手工重建 `.orig`（tar 解压 `--strip-components=1`）与 `.work` 副本后继续（工具误判已记录） |
| 7 | CI worker 缺 JDK，`install-jdk.sh` 安装在解压步报 `tar: fork: Resource temporarily unavailable`（构建 #73652/#73653 稳定复现） | CI worker 运行于 AppSpawn 沙箱、同 UID 进程限额：安装器 `tar xzf` 需 fork gzip 子进程被打满（两次并发构建叠加）；本地真机因 `~/bishengjdk17` 预存而从未触发该路径（W0b 教训） | `_ensure_java` 改为配方内纯 Python 引导：`conan download()`（进程内下载，sha256 钉校验 `ce0749…`）+ `tarfile.extractall`（进程内 zlib 解压，零 fork）+ 竞态安全 `rename` 发布；真机独立验证 285.9MB tarball 解压与 `bin/java -version` rc=0，本地 W3 复验 100% PASS |

## 源码修改

- `patches/0001-make-Platform.gmk.patch`（唯一补丁，+9 行，portability）：
  在 `make/Platform.gmk` 为 `uname -s` = `HarmonyOS` 增加平台分支，
  `OS_NAME=linux`、`OS_ARCH=$(uname -m)`、`OS_VERSION=$(uname -r)`，
  避免落入 Windows 分支的分号类路径分隔符。

## 依赖版本

- BiShengJDK 17.0.13（运行时/构建时 JDK）
- Apache Ant 1.10.15（校验 SHA1 `1b460a543caf0b2087fef210c7b4813909901fdc`）
- JT Harness jt6.0-b24 / AsmTools 9.1-b01（上游 build.sh 从 GitHub 源码构建）
- JUnit 1.14.2 / TestNG 7.3.0 / Guice 5.1.0 / JCommander 1.82（Maven Central，阿里云镜像）

## 上游测试（R51 三步法）

1. **清点**：上游自测由 `make test` 驱动（test/*.gmk 的 `*.ok` 目标）；上游 CI
   （.github/workflows/test.yml）先跑 `quick-test` 再跑全量 `test`。
2. **实际运行（HarmonyOS PC 真机）**：
   - `make quick-test`：**9/9 通过**（Basic.check / Basic.othervm / Basic.agentvm /
     i18n×3 / JUnitTrace.agentvm / tidy-docs / lockCheck）。
   - `make test`（全量，HEADLESS=1）：选中 **271** 个目标，**266 通过 / 4 失败 / 1 挂起**：
     | 目标 | 结果 | 根因（均为平台/工具语义差异，非 jtreg 功能缺陷） |
     |------|------|--------------------------------------------------|
     | CleanupTests.agentvm.retain | 失败（5 用例本身全 PASS） | 鸿蒙 chmod/只读语义受限，"不可删除文件"可被删除，scratch 目录计数 1 != 5 |
     | ExplicitIds.othervm | 挂起后终止 | `-othervm` 模式该用例挂起（>45 分钟）；`-agentvm` 同套件通过 |
     | ProblemList | 失败 | JVM `os.version` 含空格（"HongMeng Kernel 1.12.0"），OSNAME-REV 排除失配 → passed:2; excluded:4（期望 passed:1） |
     | SkippedExceptionTest.agentvm | 失败 | 设备 toybox grep 不支持 BRE `\+`，summary 正则断言无法匹配（实际结果正确） |
     | SkippedExceptionTest.othervm | 失败 | 同上 |
3. **回填**：`make quick-test` 9/9 由 `conan create` 在 build() 中执行（CI 可复现）；
   全量 271 目标统计为真机实测。

## 验证结果

```bash
# 真机构建（conan create 干净构建 + test_package 消费者测试）
conan create archives/j/jtreg8/8.3-1 -pr:h=ohos-aarch64-device -pr:b=ohos-aarch64-device
sh <pkg>/bin/jtreg -version        # jtreg 8.3+1 / BiShengJDK 17.0.13
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
- 全量自测的 4 失败/1 挂起均为环境语义差异（详见上表），`conan create` 内运行的是
  上游 `quick-test`（9/9），平台 CI 在标准 Linux 环境执行同一目标。

**编译结束**: 2026-10-04 19:58
**最终状态**: built
