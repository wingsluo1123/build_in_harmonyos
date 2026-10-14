# zt-exec

ZT Process Executor（`org.zeroturnaround:zt-exec`）是 ZeroTurnaround 的轻量级
Java 外部进程执行库：同步/异步执行外部进程，流式读取与重定向 stdout/stderr，
支持超时销毁、shutdown-hook 进程清理与进程事件监听。

- 官方源码：https://github.com/zeroturnaround/zt-exec
- 适配版本：1.12（tag `zt-exec-1.12`）
- 许可证：Apache-2.0（含 NOTICE.txt 义务：代码含 Apache Commons Exec 片段，
  包内 `licenses/` 同时收取 LICENSE 与 NOTICE.txt）
- 产物形态：架构无关的 Java 字节码 JAR，不含 OpenHarmony 原生 ELF

## OpenHarmony 适配

- JDK17 编译基线：上游 pom 的 `source/target 1.6` 被 JDK17 javac 拒绝
  （Source option 6 is no longer supported），portability 补丁就地上调 1.8。
- JDK 探测链：`JAVA_HOME` → `~/bishengjdk17` → PATH `java` → cmd-pkgs
  `install-jdk.sh` 兜底（真机无系统 JDK）；构建与上游测试 spawn 的子进程
  共用该链路。
- Maven 3.9.11 配方自取（repo1.maven.org，SHA256 钉死，`~/apache-maven-3.9.11`
  缓存复用）；不使用上游 mvnw（wrapper 钉 Maven 3.5.4，JDK17 兼容未验证）。
- HMDFS 禁 shebang exec：mvn 以 `sh $MAVEN_HOME/bin/mvn` 显式调用。
- 构建子进程 HOME：bisheng JDK 在设备上无 passwd 条目时 `user.home` 回退为
  字面 `?`，本地 Maven 仓库会散射进构建目录——构建时显式 HOME 并以
  `-Dmaven.repo.local` 绝对路径钉死。
- 上游测试厂商中性补丁：ProcessListenerThrowTest 写死 Oracle JDK
  `java version` 字面量，BiSheng 输出 `openjdk version`，0002 号 portability
  补丁扩展匹配（不改测试意图）；`os.name=HarmonyOS` 下 Assume 平台守卫用例
  按上游设计跳过（1 skipped）。

## 验证方式

- 权威 CI：`ci/conan/build_and_test.sh`（profile `ohos-aarch64`），
  L0/L1/L4 PASS。
- 上游测试：surefire 在 `mvn package` 的 test 阶段真实执行 96 个 @Test
  方法（21 个测试类、35 个测试源文件），0 失败 0 错误；1 个跳过为上游
  Assume 平台守卫（os.name=HarmonyOS）。
- test_package：真机编译运行消费者程序，经 ProcessExecutor 实际 spawn 子
  JVM，5 项 API 断言（输出重定向/exitValues/异步 start+Future/超时销毁）
  + PASS。

## 依赖

- 编译期：slf4j-api 1.7.2（构建时由 Maven Central 解析）。
- 运行期：slf4j-api 1.7.2（强制依赖，ProcessExecutor 类初始化即触 SLF4J），
  打包时一并收入包内 `libexec/`。
- 工具链（仅构建期）：BiSheng JDK 17、Maven 3.9.11。
- 上游测试期（不进包）：junit 4.11、logback-classic 1.1.2、commons-lang3 3.5、
  commons-io 2.5。

## 参考

- 上游仓库：https://github.com/zeroturnaround/zt-exec
- Maven Central：https://repo1.maven.org/maven2/org/zeroturnaround/zt-exec/
