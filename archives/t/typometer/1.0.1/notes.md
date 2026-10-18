# typometer 1.0.1 适配笔记

## 项目信息

- **软件**: typometer —— 文本/代码编辑器打字延迟（视觉延迟）分析工具（Java/Swing GUI）
- **版本**: 1.0.1
- **上游**: https://github.com/pavelfatin/typometer （tag `v1.0.1`，Apache-2.0）
- **语言**: Java（source/target 8）
- **构建系统**: Maven（`pom.xml`）
- **目标平台**: HarmonyOS PC (aarch64, JDK 17)

## 编译环境

- **JDK**: BiShengJDK 17.0.13（`~/bishengjdk17`，OHOS aarch64）
- **Maven**: apache-maven 3.9.11（配方自取，sha256 `4b7195b6...beac` 校验）
- **OS**: HarmonyOS（`os.name=HarmonyOS`，`os.arch=aarch64`）
- **网络**: Maven Central 经阿里云 central 镜像（`settings.xml` mirror），失败重试 3 次后回退直连

## 编译步骤

```bash
export JAVA_HOME=~/bishengjdk17
export PATH=$JAVA_HOME/bin:~/apache-maven-3.9.11/bin:$PATH
cd typometer-1.0.1.work
mvn -s maven-settings-aliyun.xml clean package -B -DskipTests=false
# → target/typometer-1.0.1.jar（含 JNA 的 uber-jar）
#   target/typometer-1.0.1-bin.zip（bin 分发包）
#   target/original-typometer-1.0.1.jar（未 shade 原始 jar）
```

`mvn package` 同时通过 surefire 执行全部 JUnit 用例。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 运行 Swing GUI：`UnsatisfiedLinkError: .../libfontmanager.so: Error loading shared library libfreetype.so.6` | JDK 的 `libfontmanager.so` 依赖系统 `libfreetype.so.6`，OHOS 开发镜像未预置 freetype | 记录为运行时环境项（非构建阻塞）；构建/单测/打包不含 AWT 初始化，不受影响 |
| 2 | JNA 在 OHOS 上识别异常：`Platform.isLinux()=false`、`RESOURCE_PREFIX=harmonyos-aarch64`（jar 内无该平台 dispatcher） | JNA 4.2.0 仅按 `os.name` 里的 `linux/win` 关键字判定平台，`HarmonyOS` 不匹配任何已知平台 | 见“源码修改”：显式识别 HarmonyOS，禁止选用依赖 X11 的 native 访问器 |
| 3 | Maven Central 直连偶发 `Connection reset` | OHOS 网络到 repo1.maven.org 不稳定 | 配方用阿里云 central 镜像 + 3 次重试 + 直连回退 |

以上问题 1 为运行时环境项，非构建阻塞；问题 2、3 已在配方/补丁中固化。

## 源码修改

补丁：`patches/0001-src-main-java-com-pavelfatin-typometer-screen-ScreenAccessor.java.patch`

- 文件：`src/main/java/com/pavelfatin/typometer/screen/ScreenAccessor.java`
- 内容：新增 `isHarmonyOS()`（基于 `os.name` 运行时判定），令 `isNativeApiSupported()` 在 HarmonyOS 上返回 `false`，并令 `create(true)` 在 HarmonyOS 上跳过 `WindowsScreenAccessor`/`LinuxScreenAccessor`，回退到可移植的 `AwtRobotScreenAccessor`。
- 依据（R8/R40）：HarmonyOS 虽基于 Linux 内核，但不提供 `LinuxScreenAccessor` 所需的 X11 客户端库（`libX11`），且 JNA 4.2.0 无 `harmonyos-aarch64` native dispatcher；若不显式处理，平台判定完全依赖 JNA 对 `os.name` 的脆弱字符串匹配，存在误用 native 路径而崩溃的风险。改动仅新增平台分支，不改变 Windows/Linux 既有行为。

## 依赖版本

- **编译依赖**: BiShengJDK 17.0.13、apache-maven 3.9.11（配方内 bootstrap）
- **Maven 依赖**: `net.java.dev.jna:jna:4.2.0`（编译/运行，shade 进 uber-jar）、`junit:junit:4.12`（test scope）
- **运行依赖**: JRE 17+（无独立 native 依赖；GUI 显示需平台图形栈）

## 验证结果

```bash
$ mvn clean package -B -DskipTests=false
[INFO] Tests run: 2,  Failures: 0, Errors: 0, Skipped: 0 -- CsvDataTest
[INFO] Tests run: 49, Failures: 0, Errors: 0, Skipped: 0 -- RecognitionTest
[INFO] Tests run: 37, Failures: 0, Errors: 0, Skipped: 0 -- MetricsTest
[INFO] Tests run: 1,  Failures: 0, Errors: 0, Skipped: 0 -- HeapTest
[INFO] Tests run: 89, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS

$ java -cp typometer-1.0.1.jar Probe2
os.name              = HarmonyOS
isHarmonyOS()        = true
isNativeApiSupported = false
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libexec/typometer-1.0.1.jar | ~495 KB | 含 JNA 的可执行 uber-jar（主类 `com.pavelfatin.typometer.Application`） |
| libexec/typometer-1.0.1-bin.zip | ~481 KB | 上游 assembly 生成的 bin 分发包（jar + README.html + LICENSE） |
| licenses/LICENSE | — | Apache-2.0 许可证 |

## 注意事项

- typometer 为 Swing GUI 工具，`java -jar typometer-1.0.1.jar` 需可用的图形显示服务；OHOS 开发镜像暂缺 `libfreetype.so.6` 图形字体库，GUI 运行属平台运行时环境项。
- 上游测试全部 headless（纯图像计算），在 OHOS 上可完整执行。
---

**编译结束**: 2026-10-14 13:39
**最终状态**: built
