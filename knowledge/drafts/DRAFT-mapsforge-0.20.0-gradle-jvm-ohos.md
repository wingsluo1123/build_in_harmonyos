# DRAFT-mapsforge-0.20.0-gradle-jvm-ohos

**JVM/Gradle 多模块库在 OHOS PC 的 Conan 打包**（一类问题，非单库补丁）

- 来源：mapsforge 0.20.0 适配（2026-09-30，G2/W3 逐条实证）
- 关联：`archives/v/vecmath/1.5.2`、`archives/k/ktfmt/0.64`、`archives/j/jackson-jr/2.14.0`、知识 E540

## 错误特征

```
Environment variable ANDROID_HOME needs to be set
Could not GET https://dl.google.com/dl/android/maven2/<...>.pom  → Connect timed out
Package type is 'library', but no 'shared' option declared
Project directory '.../b/build' is not part of the build defined by settings file '.../b/settings.gradle'
missing_setting_compiler missing_setting_build_type          (CI L0p)
OperatingSystem … ExceptionInInitializerError … HarmonyOS   (Gradle 不识别 HarmonyOS)
```

## 根因

1. **Android 模块**：`ANDROID_HOME` 断言 / AGP 插件在 Gradle *配置阶段*即执行；OHOS PC 无 Android SDK。
2. **google() 仓库**：Gradle 先查 `google()`，对**连接超时**（非 404）直接失败，不回退 `mavenCentral()`；
   排除 Android 模块后该仓库已无用途。
3. **Conan 契约**：`package_type="library"` 必须声明 `shared`；本地 CI 门禁 L0p 要求
   `settings` 含 `os/compiler/build_type/arch` 四项。
4. **Conan layout**：`basic_layout` 下 `self.run()` 的 cwd = `build_folder`，而 Gradle 项目根
   （`settings.gradle`）在 `source_folder`。
5. **HarmonyOS 识别**：Gradle `OperatingSystem` 类不识别 `HarmonyOS`，需给构建 JVM 注入
   `-Dos.name=Linux`。

## 推荐方案（`gradle-jvm-ohos-recipe`）

| 步骤 | 做法 |
|---|---|
| 补丁 | `settings.gradle` 去掉 Android 模块 `include` 与 `google()`；`build.gradle` 去掉 AGP 插件块（**仅构建系统层面，无平台宏**） |
| 配方头部 | `package_type="library"`；`settings = "os","compiler","build_type","arch"`；`options={"shared":[True,False]}` |
| 工具链 | `build_requirements()` → `tool_requires("gradle/8.12")`（ohpcd 已发布，免系统 Gradle）；JDK 按 `vecmath` 先例自举 BiSheng JDK 17.0.13（sha256 固定） |
| build() | 设 `JAVA_HOME` / `PATH` / `GRADLE_USER_HOME=<source_folder>/.gradle-home` / `JAVA_TOOL_OPTIONS=-Dos.name=Linux`，然后 `gradle -p "<source_folder>" clean build --no-daemon --console=plain` |
| package() | 收集各模块 `build/libs/*.jar` 到 `lib/jar/`；`package_info()` 暴露 `MAPSFORGE_JAR_DIR` / `MAPSFORGE_CLASSPATH`，`cpp_info` dirs 置空 |
| test_package | `javac`+`java` 跑真实 API 断言，含 **≥1 鸿蒙特有断言**（BiSheng JDK / HarmonyOS 运行时） |

## 验证

```
conan-verify: G1/G0/G2/G3/G4 PASS
W3 本地 CI:   L0/L1 PASS，Pass rate 100%
上游 JUnit4:  235/235 PASS
```

## 适用性

含 Android 子模块的 Java/Kotlin Gradle 桌面库；纯 JVM 库同理（省去 Android 排除步骤）。
JAR 为架构无关字节码，不涉及 OHOS C/C++ 交叉工具链。

## 备注（本环境取证）

- **上游测试 N 申报口径**（外部审查 `pc-pr-review` rule4 按“源码静态清点”独立复算，声明值必须 ≥ 清点值，
  否则按*少报*驳回）：JUnit/Gradle 库按 `@Test` **全量**（含上游自身注释禁用的 `@Test`）计，
  再加 `src/androidTest` 仪器测试文件数。本库 = `@Test` 244 + androidTest 9 = **253**（其中可执行 235）。
  本库 `map-writer` / `poi` 分别有 8、1 处 `// @Test` 被上游注释禁用——朴素 `grep @Test` 会命中，
  但运行期不注册，必须显式写入口径与差异来源。
- 官方 GitHub 源码通道不可达时，本地验证可用 conan `core.sources:download_cache`（按 sha256 索引，
  字节与官方一致）；CI 侧由 `ci/conan/build_and_test.sh` 的 mirror fallback（gh-proxy）自动改写。
- `conandata.yml` 在 W3 后被 mirror 重写为 url 列表（含 `gh-proxy.com`）且 `.orig` 残留时，提交前
  必须还原为官方单一 URL（否则违反 R39/PF7）。
