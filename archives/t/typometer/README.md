# typometer

Text / code editor **typing latency analyzer** —— 由 Pavel Fatin 开发的 Java/Swing 桌面工具，用于测量并分析文本/代码编辑器的视觉输入延迟（击键到字符显示的延迟），支持同步/异步测量模式、CSV 导入导出、频率分布与对比图表。

## 功能概述

- 自动生成键盘输入事件并用屏幕截图捕获，全自动测量编辑器打字延迟
- 支持原生屏幕访问 API（Windows GDI / Linux X11）与 AWT Robot 回退
- 同步 / 异步两种测量模式，CSV 数据导入导出
- 汇总统计、频率分布、折线/柱状图（含对比图），图表可导出 PNG

## 已编译版本

- **1.0.1** (2026-10-14) — BiShengJDK 17.0.13 + Maven 3.9.11 构建，产物为含 JNA 的可执行 uber-jar（aarch64）

## 关键信息

- **源码**: https://github.com/pavelfatin/typometer （tag `v1.0.1`）
- **许可证**: Apache-2.0
- **构建系统**: Maven（`pom.xml`；maven-shade-plugin 生成 uber-jar，maven-assembly-plugin 生成 bin 分发包）
- **依赖**: `net.java.dev.jna:jna:4.2.0`、`junit:junit:4.12`（test）
- **平台**: HarmonyOS / OpenHarmony PC (aarch64, JDK 17)
- **产物**: `libexec/typometer-1.0.1.jar`（主类 `com.pavelfatin.typometer.Application`）、`libexec/typometer-1.0.1-bin.zip`

## 鸿蒙适配要点

1. **平台识别适配**：`ScreenAccessor` 显式识别 HarmonyOS/OHOS（`os.name` 运行时判定），在 HarmonyOS 上禁用 `LinuxScreenAccessor`（依赖 X11/libX11）与 `WindowsScreenAccessor`，回退到可移植 `AwtRobotScreenAccessor`，避免误用不存在的 native 库
2. **JNA 限制**：JNA 4.2.0 按 `os.name` 关键字判定平台，`HarmonyOS` 不匹配任何已知平台（`Platform.isLinux()=false`，`RESOURCE_PREFIX=harmonyos-aarch64` 无对应 native dispatcher）
3. **Maven 镜像**：Maven Central 直连在 OHOS 网络偶发重置，配方经阿里云 central 镜像构建并带重试/回退
4. **运行环境项**：Swing GUI 需要平台图形显示服务与 `libfreetype.so.6`（JDK `libfontmanager.so` 依赖），OHOS 开发镜像暂缺，属运行时环境限制，不影响构建/单测/打包

## 测试

- **上游测试**: JUnit 4.12，surefire 执行 **89** 个用例（`CsvDataTest` 2、`MetricsTest` 37、`RecognitionTest` 49、`HeapTest` 1），全部 headless 纯计算，OHOS/aarch64 上全绿
- **test_package**: 编译并运行 Java 消费者程序（**自包含，无外部夹具**），加载打包 JAR、调用公开 API（`SummaryStatistics`/`Series`/`ChartData`/`FrequencyDistribution`）、断言 HarmonyOS 平台识别（含 2 项鸿蒙专用断言，共 19 断言）

## 依赖关系

- **编译依赖**: BiShengJDK 17.0.13、apache-maven 3.9.11（配方内 bootstrap）
- **运行依赖**: JRE 17+（GUI 显示需平台图形栈）

## 参考资料

- **源码仓库**: https://github.com/pavelfatin/typometer
- **Release v1.0.1**: https://github.com/pavelfatin/typometer/releases/tag/v1.0.1
