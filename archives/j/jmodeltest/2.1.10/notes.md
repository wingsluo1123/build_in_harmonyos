# jmodeltest 2.1.10 — HarmonyOS 适配笔记

## 库概述
- **用途**：ModelTest 的参考实现，统计选择核苷酸/蛋白质进化模型。
- **上游**：https://github.com/ddarriba/jmodeltest2 ，tag `v2.1.10r20160303`。
- **形态**：纯 Java 桌面/命令行工具（Ant 构建，javac + jar → `dist/jModelTest.jar`），
  自带 7 个 vendor jars（lib/：pal、mpj、alter、freemarker、BrowserLauncher2-all、
  jfreechart-1.0.14、jcommon-1.0.17）。
- **运行时**：JVM → bishengjdk 17（系统工具，aladin/alloy 同款自动探测/下载）。

## 适配要点（路径 A — 基础适配）
1. **构建**：手动复刻 `build.xml`（aladin 模式）——`subprocess` 跑 javac + jar，
   无需 Ant/Gradle bootstrap。
   - 上游 `-source/-target 1.6` 已被 JDK 17 移除 → 降级用 **1.8** 编译（Java 17 最低支持 1.7）。
   - `-jar`` 打包与上游完全相同：classes + `src/main/resources` 的
     `conf/resources/extra/example-data/trees` 并入 jar；Main-Class +
     `Class-Path: lib/*.jar`（7 个 vendor jar 放 `libexec/` 同级）。
2. **运行时/os.name**：PAL 与 AWT 解析平台依赖 `os.name`；launcher 设
   `JAVA_TOOL_OPTIONS=-Dos.name=Linux`（alloy 技巧），wrapper 自动定位 bishengjdk。
3. **无头消费者用例**：`-getPhylip` 只做比对文件读取→Phylip 转换→写 `.phy` 文件，
   **不需要 phyml 外部二进制**；CLI 自带 `GraphicsEnvironment.isHeadless()` 守卫。
   完整 model-selection（`RunPhyml*`）需要外部 phyml——OHOS 无该二进制，故采用
   `-d <alignment> -getPhylip` 作端到端用例。

## 与上游差异
- `-source/-target`：1.6 → 1.8（JDK17 编译兼容，行为等价）。
- 未打包 `src/main/resources/exe/`（仅含 phyml README，无二进制，无用）。
- 其余逻辑无改动；重打包，不修改任何上游源码/测试。

## 测试
- 上游无正式测试套件（无 `src/test`，无 JUnit）。
- 本配方 test_package 用打包产物的 launcher 跑：
  - `-help` 打印 usage（JVM+jar+classpath 冒烟）
  - `-d 18S_insects2.nex -getPhylip` 真实转换（写 `.phy`），端到端消费者验证。
- 详见 `test_package/MANIFEST.yml` 与 `test_package/test.sh`。

## 门禁/CI
- settings 全量声明（os/compiler/build_type/arch）满足 L0p 门禁。
- package_type=application，JVM 工具惯例。
- JDK17 下载来源：cmd-pkgs release（aladin/alloy 同源），本机 CI 已验证 200 可下载。