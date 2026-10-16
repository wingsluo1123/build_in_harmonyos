# mapsforge — OpenHarmony PC 适配

mapsforge 是一个用于 **OpenStreetMap 二进制矢量地图（`.map`）** 的 Java 库：读取、
渲染与写地图文件（`mapsforge-core` / `map` / `map-reader` / `map-awt` /
`map-writer` / `themes` / `poi*`）。上游是 **Gradle 多模块** Java 工程。

- 官方源码：https://github.com/mapsforge/mapsforge
- 官方 tag 归档：https://github.com/mapsforge/mapsforge/archive/refs/tags/0.20.0.tar.gz
- 许可证：LGPL-3.0-or-later
- 上游版本：0.20.0（tag `0.20.0` → commit `40a8f86df5ff9e29bb297f440d1d25b90be186aa`，release 2023-08-15）
- 构建系统：Gradle（wrapper 声明 8.0；本环境用 ohpcd `gradle/8.12` 执行）
- Java 基线：`sourceCompatibility/targetCompatibility = 1.8`（`--release 8`）

## OpenHarmony 适配

上游 `settings.gradle` 声明 **13 个模块**，其中 3 个是 Android 专用：

| 模块 | 插件 | OHOS PC 处理 |
|---|---|---|
| mapsforge-map-android | java-library（依赖 `$ANDROID_HOME/platforms/android-34/android.jar`，无 ANDROID_HOME 即抛异常） | **排除** |
| mapsforge-poi-android | java-library（同上） | **排除** |
| mapsforge-samples-android | com.android.application（AGP） | **排除** |
| 其余 10 个模块（core / map / map-reader / map-awt / map-writer / themes / poi / poi-awt / poi-writer / samples-awt） | java-library / application | **构建** |

HarmonyOS PC 环境没有 Android SDK，因此：

1. **排除 3 个 Android 模块**（`patches/0002-settings.gradle.patch`）；
2. **移除 `google()` Maven 仓库**（仅 Android/AGP 需要；该仓库在 OHOS 构建网络不可达，
   Gradle 对*连接超时*（非 404）会直接中断整个依赖解析）；
3. **移除 Android Gradle Plugin 插件块**（`patches/0001-build.gradle.patch`，已无 Android 模块应用它）；
4. 顺带把 `group version` 从 `master-SNAPSHOT` 固定为 `0.20.0`，使产物名与官方发布物一致
   （`mapsforge-*-0.20.0.jar`）。

**工具链**：

- **JDK**：使用 SHA-256 固定的 BiSheng JDK 17.0.13（ohos-aarch64）；
  系统已存在 `JAVA_HOME`/`~/bishengjdk17` 时复用，否则按 `conandata.yml` 的
  `build_tools.bisheng_jdk` 下载并校验。策略与 `archives/v/vecmath/1.5.2` 一致。
- **Gradle**：`tool_requires("gradle/8.12")`（ohpcd 制品仓已发布），
  由 Conan 注入到构建环境，无需系统安装 Gradle，也无需上游 wrapper 联网下载分发。

**产物**：Conan 包内 `lib/jar/` 存放 10 个 JAR（架构无关的 Java 字节码，不含 ELF），
`package_info()` 暴露 `MAPSFORGE_JAR_DIR` 与 `MAPSFORGE_CLASSPATH`。

## 上游测试

上游测试为 **JUnit 4**（`./gradlew test` / `gradle build`）。适配环境实测：

- 命令：`gradle clean build`（含全部 10 个模块的 `test` 任务）
- **计数口径（源码静态清点 N）**：`@Test` 全量 **244**（有效 235 + 上游自身注释禁用 9：
  `map-writer/MapFileWriterTest` 8 处、`poi/PoiCategoryRangeQueryGeneratorTest` 1 处）
  + `src/androidTest` 仪器测试文件 **9** = **253**；其中 OHOS PC 可执行 = 有效用例 **235**
- 可执行用例：**235 / 235 通过**（失败 **0**，错误 **0**，跳过 **0**）；
  9 处注释禁用项上游本就不注册，9 个 `androidTest` 需 Android 设备/SDK
- 逐条清单：`0.20.0/reports/testcases.tsv`；原始日志：`0.20.0/reports/upstream-tests.log`

## test_package

`test_package/TestMapsforge.java` 对打包 JAR 做 15 项真实 API 断言
（`LatLong` / `BoundingBox` / `LatLongUtils`），其中 `test_ohos_bisheng_jdk`
为**鸿蒙特有**断言（校验运行在 HarmonyOS BiSheng JDK 上），满足 R34 与
"鸿蒙特有用例 ≥1" 要求。
