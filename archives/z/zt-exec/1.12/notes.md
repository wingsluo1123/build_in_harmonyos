# notes — zt-exec 1.12 (OHOS HarmonyOS PC, aarch64)

## 定位

`org.zeroturnaround:zt-exec` 是纯 Java 进程执行库（jar 产物），无 native 代码。
OHOS 适配 = 源码编译 + 上游测试真机执行 + 可运行 JAR 打包（含运行时依赖）。

## 源码与身份

- 上游 GitHub tag `zt-exec-1.12`（commit 763497ed4a4e60cc2847d87da2a0773e8ea6eb66）。
- tarball SHA256 `59e89dfe…4ed4de`（本地下载与设备侧 gh-proxy 通道各校验一次一致）。
- License Apache-2.0；根目录 NOTICE.txt（带 .txt 后缀，Apache Commons Exec 片段声明），
  package() 同时收取 LICENSE 与 NOTICE.txt。

## 构建链

- JDK：设备 `JAVA_HOME`（~/.zshrc 已置 `/storage/Users/currentUser/bishengjdk17`）；
  配方 _ensure_java 探测链 JAVA_HOME → ~/bishengjdk17 → PATH java → cmd-pkgs 自装。
  上游测试 spawn 子进程用裸 `java`，因此 build() 把 JAVA_HOME/bin 前置进 PATH。
- Maven：**不用上游 mvnw**。wrapper 钉 Maven 3.5.4 且下载源
  repo.maven.apache.org 在设备上未验证可达；Maven 3.5.4 + JDK 17 组合也未验证。
  配方自取 Maven 3.9.11（repo1.maven.org，sha256 钉死，与 jackson/jakarta 系列先例
  一致），解压 `~/apache-maven-3.9.11` 缓存复用；HMDFS 禁 shebang，`sh .../bin/mvn` 调用。
- 补丁一（构建）：pom.xml maven-compiler-plugin source/target `1.6 → 1.8`
  （JDK 17 javac 拒绝 source 6）。
- 补丁二（测试可移植性）：ProcessListenerThrowTest 的版本串匹配扩展
  `openjdk version`。该测试期望 listener.afterFinish 抛 InvalidOutputException，
  触发条件写死 Oracle JDK 的 `java version` 字面量；BiSheng JDK（OpenJDK 系）
  输出 `openjdk version`，首跑 2 个 @Test 失败（Expected exception:
  InvalidOutputException）。补丁只扩展匹配字符串，测试意图（listener 异常传播）
  在任何 JDK 厂商下不变。
- javadoc：maven-javadoc-plugin 3.0.1 attach 在 package 阶段；产物不需要 javadoc
  jar，`-Dmaven.javadoc.skip=true` 跳过，避免 JDK 17 doclint 对 2013 年注释风格的
  无谓报错。surefire 未在 pom 声明，由 Maven 3.9.11 默认生命周期提供
  （3.2.5，JDK 17 安全）。

## 上游测试（真实执行）

- `mvn -B clean package -DskipTests=false`：surefire 在 test 阶段先跑
  21 个测试类 / 96 个 @Test（JUnit 4.11）。
- 测试会 spawn 真实子 JVM：`java -cp target/test-classes <Helper>`（HelloWorld、
  PrintArguments、Loop、BigOutput、WriterLoop 等 helper 均无三方依赖）；
  外部命令依赖仅 `java`、`sleep`（TimeoutTest issue56）、`/bin/true`
  （InputRedirectTest）——设备实测均可执行。
- 首跑结果：96 执行 = 93 过 + 1 跳过（InputRedirectTest：os.name=HarmonyOS
  触发上游 Assume 平台守卫，属设计行为）+ 2 失败（ProcessListenerThrowTest，
  见补丁二）。补丁后全绿。
- os.name 在 BiSheng JDK/OHOS 上为 `HarmonyOS`（`-XshowSettings:properties`
  实测），不是 Linux —— 影响 SystemUtils 分支的测试都按此理解。
- 慢设备抖动面：TimeoutTest 用 1s 超时销毁 `sleep 3`，ShutdownHookTest 起
  WriterLoop 后 sleep 2s 校验文件不再增长；首跑均稳定通过。

## 打包

- `libexec/zt-exec-1.12.jar` + `libexec/slf4j-api-1.7.2.jar`（强制运行时依赖，
  ProcessExecutor 类初始化即触 SLF4J；从构建后的 ~/.m2 收集，leakcanary-shark
  收集 kotlin-stdlib 同范式）。
- `licenses/LICENSE` + `licenses/NOTICE.txt`。
- `cpp_info.libdirs = ["libexec"]`；库包，无 commands.json（R38）。

## test_package（真机消费者验证）

`test.sh` 编译运行 `TestZtExec.java`：经 ProcessExecutor 真实 spawn 子 JVM ——
同步 execute + redirectErrorStream + readOutput（`java -version`）、exitValues
校验、start()+getFuture() 异步 API、timeout(1s) 销毁 30s 长跑进程
（TimeoutException 断言）。共 9 项断言（2 JAR 存在 + 1 编译 + 5 API + 1 PASS）。
