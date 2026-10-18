# jheaps — OpenHarmony PC 适配

JHeaps 是纯 Java 的堆数据结构库（org.jheaps），提供数组二叉/d-ary 堆、
树形配对堆/斐波那契/左倾/斜堆、单调 radix 堆（Dijkstra 最短路经典支撑件）、
软堆与可合并堆等，是 JGraphT 等图算法库的底层依赖。

- 官方源码：https://github.com/d-michail/jheaps
- 官方 tag 归档：
  https://github.com/d-michail/jheaps/archive/refs/tags/jheaps-0.14.tar.gz
- 归档 SHA-256：
  `e09aa581818a220257d3ab17e3a6c54fefe8d1419228c40536eb5514a7fb3022`
- 许可证：Apache-2.0
- 上游版本：0.14（2020-06-25，与 Maven Central org.jheaps:jheaps:0.14 同一发布）
- Java 基线：Java 8 字节码（major 52），零编译/运行期第三方依赖

## OpenHarmony 适配

本配方在设备上以 SHA-256 固定的 BiSheng JDK 17.0.13 + Apache Maven 3.8.6
从官方 tag 源码构建单模块 jar（`lib/jheaps-0.14.jar`，88 个 class），
并在 build() 内跑完上游完整 JUnit 套件（51 个 Surefire 套件、1391 个执行
用例、0 失败/错误/跳过）。JAR 是架构无关的 Java 字节码，无 ELF 产物、
无 JNI/native。

### 平台差异要点

- **构建工具供给**：OHOS 设备无预装 Maven 且上游 tarball 不含 Maven
  Wrapper；配方经 conandata `build_tools.maven` 以固定 URL+SHA-256 下载
  Apache Maven 3.8.6 二进制（repo1.maven.org，sha512 与 Apache 官方发布值
  位级核对一致），先探测 `MAVEN_HOME`/`M2_HOME`/PATH 再下载，与 JDK 供给
  链同构。
- **user.home="?" 坑**：OHOS 设备 JVM（uid 不在 /etc/passwd）报告
  `user.home="?"` 且不回退读 HOME；构建显式传
  `-Duser.home=<build 目录>` 与 `-Dmaven.repo.local=<build>/m2-repository`。
- **os.name 归一**：`-Dos.name=Linux` 经 `JAVA_TOOL_OPTIONS` 注入 Maven 与
  Surefire fork JVM；test_package 消费者同样注入并回读断言。
- **JDK 17 兼容补丁**：上游 maven-bundle-plugin 4.2.1（bnd 5.2）在
  JDK 9+ 的 `TreeMap.computeIfAbsent` 自变更检测下于 process-classes 阶段
  抛 ConcurrentModificationException（FELIX-6259/JDK-8176894）；补丁将插件
  版本属性升至 5.1.9（OSGi 指令不变，jar 仍带
  `Automatic-Module-Name: org.jheaps`）。
- **测试口径**：`mvn clean package`——test 阶段跑完整上游套件、package 阶段
  产 OSGi jar；上游 jacoco 0.75 覆盖率门绑定在 verify，属发布质量门而非
  库行为，刻意不进入本配方验证口径（已在 MANIFEST/notes 披露）。静态
  428 个 @Test 源方法经 JUnit 继承（8 个抽象基类）扇出为 51 套件 1391 个
  执行用例，配方按 surefire XML rerun-aware 逐用例钉死。

## 使用方式

```bash
javac -cp jheaps-0.14.jar Example.java
java -cp ".:jheaps-0.14.jar" Example
```

Conan 包同时通过构建与运行环境公开 `JHEAPS_JAR`，其值指向
`jheaps-0.14.jar`。

## 版本

| 版本 | 状态 | 日期 |
|---|---|---|
| 0.14 | built | 2026-10-14 |
