# DRAFT — OHOS 真机 Java/Maven（JAR 应用）适配：镜像构建 + surefire 上游测试 + libexec 打包

状态：草稿（OpenDesk 落稿，2026-10-14）；Exxx 编号由知识库主编定稿时分配。
案例库：typometer 1.0.1（pavelfatin/typometer，Java 8 Swing，Maven，JNA 4.2.0）。

## 可复现症状与稳定错误签名

- Maven 依赖下载失败（直连 Central）：`Connection reset` / `Read timed out` 于
  `https://repo1.maven.org/maven2/...`。
- 源码下载失败（直连 GitHub）：`Failed to connect to github.com port 443`。
- Swing GUI 运行首错：
  `java.lang.UnsatisfiedLinkError: .../libfontmanager.so: Error loading shared library libfreetype.so.6`
  （AWT 字体子系统初始化时）。

## 根因（机理链）

1. OHOS 真机到 `repo1.maven.org` 的直连不稳定，需经镜像（阿里云 central）并带重试与直连回退；
   GitHub 直连不可达，源码 tarball 走镜像通道（配方 `conandata.yml` 保留官方 URL，镜像由 CI/工具注入）。
2. 工具链：JDK 需定位 `JAVA_HOME`（bishengjdk 17）；上游未附带 `mvnw`，配方自取 `apache-maven 3.9.11`
   并 sha256 钉校验后解压使用。
3. `mvn package` 经 maven-surefire 真实执行上游 JUnit 用例（typometer 89 例），maven-shade-plugin
   生成含依赖的 uber-jar，maven-assembly-plugin 生成 bin 分发包；产物中 `src/main` 为主 jar，测试在
   `src/test`，全部 headless 纯计算。
4. JAR 属库包产物 → 置于 `libexec/`，`package_info()` 置 `cpp_info.libdirs=["libexec"]`（R38 无需 commands.json）。
5. Swing/AWT GUI 运行时：JDK 的 `libfontmanager.so` 依赖系统 `libfreetype.so.6`，OHOS 开发镜像未预置，
   且 GUI 还需图形显示服务 → 运行期 `UnsatisfiedLinkError`。**该依赖仅在 AWT 初始化时触发**，headless
   上游测试与消费者测试不做 AWT 初始化，故不受影响。

## 方案

配方 `build()`：

```python
apply_conandata_patches(self)
java_home = self._ensure_java()          # 定位 bishengjdk17（JAVA_HOME / ~/bishengjdk17）
maven_home = self._ensure_maven()        # 自取 apache-maven-3.9.11，sha256 校验
save(self, settings_xml, "<mirror> aliyun central mirrorOf=central </mirror>")
self.run('bash -c "cd {src} && sh {mvn} -s {settings}.xml clean package -B -DskipTests=false"',
         env="conanbuild")               # 失败重试 3 次后直连回退
# 解析 target/surefire-reports/*.txt → 汇总上游用例数并打印 HMBS_UPSTREAM_TEST_RESULT
```

`package()`：`target/typometer-<ver>.jar` 与 `-bin.zip` 拷入 `libexec/`，`LICENSE` 拷入 `licenses/`。

## 影响面

适用于所有在 HarmonyOS PC (aarch64) 上以 Maven 构建的 Java 库/应用。

## 验证

- `mvn clean package -B -DskipTests=false` → `BUILD SUCCESS`；surefire 汇总 `Tests run: 89,
  Failures: 0, Errors: 0, Skipped: 0`（CsvDataTest 2 / MetricsTest 37 / RecognitionTest 49 / HeapTest 1）。
- `conan-verify` 八门禁（G0–G4 + L2/L4/L5）PASS。
- test_package 消费者测试加载打包 JAR 并调用 `Metrics.detect()`，9/9 断言通过（含鸿蒙专用断言）。

## 禁则

- ❌ 用 `-DskipTests` 跳过上游测试后声称适配完成（掩盖回归，违反 R51/R34）。
