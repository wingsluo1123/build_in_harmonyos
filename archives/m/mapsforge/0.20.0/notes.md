# mapsforge 0.20.0 适配笔记

## 编译环境
- 构建系统: gradle（上游 Gradle 多模块；本环境用 ohpcd `gradle/8.12` 执行）
- JDK: BiSheng JDK 17.0.13（ohos-aarch64，SHA-256 固定，来自 conandata build_tools）
- 编译日期: 2026-09-30
- 编译器: N/A（纯 Java，无 C/C++ 交叉编译）
- 状态: built

## 编译步骤

```bash
# 1. 获取源码（官方 tag 归档，sha256 已校验）
#    https://github.com/mapsforge/mapsforge/archive/refs/tags/0.20.0.tar.gz
# 2. 应用平台补丁（排除 Android 模块 + 去 google() 仓库 + 去 AGP 插件块）
# 3. 构建（Conan 内等价命令）
JAVA_HOME=~/bishengjdk17 \
JAVA_TOOL_OPTIONS="-Dos.name=Linux" \
GRADLE_USER_HOME=<src>/.gradle-home \
gradle -p <src> clean build --no-daemon --console=plain
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Could not GET https://dl.google.com/dl/android/maven2/org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.pom` → Connect timed out，构建失败 | `settings.gradle` 的 `dependencyResolutionManagement` 同时声明 `google()` 与 `mavenCentral()`；Gradle 先查 google()，对*连接超时*（非 404）直接判失败，不回退 | 排除 Android 模块后 `google()` 已无用途 → 补丁移除（`patches/0002-settings.gradle.patch`） |
| 2 | `throw new GradleException("Environment variable ANDROID_HOME needs to be set ...")` | `mapsforge-map-android` / `mapsforge-poi-android` 在配置阶段即断言 ANDROID_HOME；`mapsforge-samples-android` 应用 AGP | OHOS PC 无 Android SDK → 补丁从 `settings.gradle` 排除这 3 个模块（同上），并移除 root `build.gradle` 的 AGP 插件块（`patches/0001`） |
| 3 | `Project directory '.../b/build' is not part of the build defined by settings file '.../b/settings.gradle'` | Conan `basic_layout` 下 `self.run()` 的 cwd = build_folder，而 Gradle 项目根（settings.gradle）在 source_folder | `gradle -p "$self.source_folder" ...` |
| 4 | `Package type is 'library', but no 'shared' option declared` | Conan 对 `package_type = "library"` 要求声明 `shared` 选项 | `options = {"shared": [True, False]}`（JVM 包不实际使用该选项，仅为满足契约） |
| 5 | 上游 `-Dos.name` 需覆盖 | Gradle 的 `OperatingSystem` 类不识别 `HarmonyOS`，会抛 `ExceptionInInitializerError` | 构建期注入 `JAVA_TOOL_OPTIONS=-Dos.name=Linux`（ohpcd `gradle/8.12` 启动器已内置，recipe 再兜底且避免重复） |
| 6 | 本机无法下载官方 GitHub 归档 | 本环境 `codeload.github.com` 连接失败/限速（~29KB/s，且不支持 Range 续传）、`git clone` early EOF、`raw.githubusercontent.com` 超时 | 本地验证使用 conan 的 `core.sources:download_cache`（按 sha256 索引，字节与官方一致）；CI 侧由 `ci/conan/build_and_test.sh` 的 mirror fallback（`gh-proxy.com`）自动改写 `github.com` URL |

## 源码修改

仅构建系统层面（无平台宏、无空壳 stub）：

- `patches/0001-build.gradle.patch`：移除 `plugins { id 'com.android.application' version '8.0.2' apply false }`；`version = 'master-SNAPSHOT'` → `'0.20.0'`。
- `patches/0002-settings.gradle.patch`：`dependencyResolutionManagement.repositories` 去掉 `google()`；`include` 去掉 `:mapsforge-map-android` / `:mapsforge-poi-android` / `:mapsforge-samples-android`。

## 依赖版本

- Conan: `gradle/8.12`（tool_requires，ohpcd）；无其他 conan 依赖。
- Maven（Gradle 从 Maven Central 解析）: kxml2 2.3.0、svgSalamander 1.1.3、guava 28.1-jre、trove4j 3.0.3、jts-core 1.16.1、osmosis-core 0.47、sqlite-jdbc 3.28.0、activation 1.1.1、jaxb-runtime 2.3.2；测试 junit 4.12、commons-io 2.5、jetty 6.1.26、slf4j-log4j12 1.7.28。

## 验证结果

```bash
$ gradle clean build --no-daemon --console=plain
BUILD SUCCESSFUL in 24s
53 actionable tasks: 53 executed
# 测试：235 用例 / 235 通过 / 0 失败 / 0 错误 / 0 跳过
#   日志 reports/upstream-tests.log；逐条清单 reports/testcases.tsv

$ conan create archives/m/mapsforge/0.20.0 -pr:h/-pr:b ci/conan/profiles/ohos-aarch64 --build=missing
# G2 PASS（含 test_package：15 项 API 断言全通过，含 1 项鸿蒙特有断言）
```

## 上游测试计数口径（N）

| 口径 | 数值 | 说明 |
|---|---|---|
| 源码静态清点 N（外部审查口径） | **253** | `@Test` 全量 244 + `src/androidTest` 仪器测试文件 9 |
| 其中 `@Test` 全量 | 244 | = JUnit4 有效 235 + 上游自身注释禁用 9 |
| 其中注释禁用 `@Test` | 9 | `map-writer/MapFileWriterTest` 8 处 + `poi/PoiCategoryRangeQueryGeneratorTest` 1 处（`// @Test`，运行期不注册） |
| 其中 `src/androidTest` | 9 | 8 个 Robotium 测试类 + 1 个 `TestUtils`；需 Android 设备/SDK |
| OHOS PC 可执行 N | **235** | = 244 − 9；`gradle clean build` 实测 235/235 通过 |
| 适配后新增 | 1 | 鸿蒙特有 `test_ohos_bisheng_jdk` |

差异来源：9 处注释禁用项上游自身即不执行；9 个 androidTest 需 Android SDK，OHOS PC 不可运行。逐条清单 `reports/testcases.tsv`（235 行数据）。

## 交付物

| 文件 | 说明 |
|------|------|
| lib/jar/mapsforge-{core,map,map-reader,map-awt,map-writer,poi,poi-awt,poi-writer,samples-awt,themes}-0.20.0.jar | 10 个架构无关 JAR |

## 注意事项

- 上游 `src/androidTest`（9 个仪器测试文件）因排除 Android 模块**未执行**：需要 Android 设备/SDK，OHOS PC 环境不可运行。桌面/JVM 模块的 JUnit4 已全部执行（235 项）；另有 9 处上游注释禁用的 `@Test` 本就不注册（见上“计数口径”）。
- 上游 wrapper 声明 Gradle 8.0；本环境用 `gradle/8.12`（`services.gradle.org` 官方分发在本环境超时）。构建脚本未出现与 8.12 不兼容的用法。
---

**编译结束**: 2026-10-05 11:39
**最终状态**: built
