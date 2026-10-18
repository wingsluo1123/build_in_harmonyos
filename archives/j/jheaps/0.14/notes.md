# jheaps 0.14 适配笔记

## 来源与许可证

- 官方仓库：`https://github.com/d-michail/jheaps`
- 官方 tag：`jheaps-0.14`（2020-06-25）
- 官方源码归档：
  `https://github.com/d-michail/jheaps/archive/refs/tags/jheaps-0.14.tar.gz`
- 官方源码归档 SHA-256：
  `e09aa581818a220257d3ab17e3a6c54fefe8d1419228c40536eb5514a7fb3022`
  （Scout 双端复验；tag 根 pom 与 Maven Central org.jheaps:jheaps:0.14
  发布 pom 字节一致，pom sha256 `1607b620e1f2b4e1a0f4891010b3490b1fb4a83e713ac4d38b08dc2c67fa3e51`）
- 许可证：Apache-2.0（源码根 `LICENSE` 进入 Conan 包 `licenses/`）

## 打包形态

单模块 Maven 工程，`package()` 只拷贝一个精确 JAR：

- `jheaps-0.14.jar`：97 entry / 88 class，全部 Java 8 字节码（major 52），
  OSGi bundle manifest（`Automatic-Module-Name: org.jheaps`）由
  maven-bundle-plugin 生成。

零 compile/runtime 依赖；test 依赖仅 junit 4.13（构建期解析）。无 JNI/native
（`System.load|loadLibrary|native` 全零命中），纯 jar 交付不触发 E083 ELF 签名。

## 构建设置（OHOS 专属）

- 构建与 test_package 共用 SHA-256 固定的 BiSheng JDK 17.0.13
  OpenHarmony AArch64 归档（conandata `build_tools.bisheng_jdk`），
  先探测 `JAVA_HOME`/常见安装位/PATH，全部缺失时校验下载。
- **Maven 供给（本配方新增面）**：jheaps tarball 不含 `.mvn/wrapper`
  与 `mvnw`（jline3 的 wrapper 路线不可用），设备亦无预装 Maven（全盘
  find 无命中；E184 场景）。配方经 conandata `build_tools.maven` 以下列
  固定值下载 Apache Maven 3.8.6 二进制到构建目录：
  - url: `https://repo1.maven.org/maven2/org/apache/maven/apache-maven/3.8.6/apache-maven-3.8.6-bin.tar.gz`
  - sha256: `c7047a48deb626abf26f71ab3643d296db9b1e67f1faa7d988637deac876b5a9`
  - 交叉验证：设备自算 sha1 == repo1 发布 `.sha1`
    （`fcb2cda9163991b12028d2480b9e60105190eda9`）；sha512 == Apache 官方
    archive.apache.org 发布值（`f790857f...d0f91c26`）位级一致。
  - 先探测 `MAVEN_HOME`/`M2_HOME`/PATH 上的 mvn（要求 3.8+），全部缺失才
    下载；与 jline3 的 JDK 供给链同构。
- **`user.home` 坑**（继承 jline3/经验仓结论）：OHOS 设备 JVM 报告
  `user.home="?"` 且不回退读 HOME；配方显式传 `-Duser.home=<build 目录>`
  与 `-Dmaven.repo.local=<build>/m2-repository`，构建自包含可重现。
- `-Dos.name=Linux` 通过 `JAVA_TOOL_OPTIONS` 注入（Surefire fork JVM 同样
  继承）；test_package 消费者 JVM 同样注入并回读 `os.name` 断言。
- `-Dmaven.javadoc.skip=true`（预防性；上游 javadoc 插件仅在 release
  profile 绑定，日常构建不触发）。
- Maven 自身启动时 jansi 本地库加载失败（E083 自签名 .so 拒载）为已知
  非致命降级，`-B -Dstyle.color=never` 下无影响。

## JDK 17 兼容补丁（patches/0001-jdk17-felix-bundle-plugin-compat.patch）

上游 `maven-bundle-plugin 4.2.1`（内嵌 bnd 5.2）的
`aQute.bnd.osgi.Jar.putResource` 在 `TreeMap.computeIfAbsent` 的映射函数里
修改自身 map；JDK 9+ 的专用实现（JDK-8176894）检测该自变更即抛
ConcurrentModificationException，`manifest` 目标在 process-classes 阶段
（测试之前）必然失败——本 run 首次上游构建实测命中（堆栈：
`TreeMap.callMappingFunctionWithCheck -> Jar.putResource`）。

- 排障链记录：①build-chain-pitfalls/knowledge/experience 检索无既有解法
  （Java 域无命中）；②联网命中官方 FELIX-6259 与修复线说明
  （maven-bundle-plugin 5.1.1+ 支持 JDK 11+ 构建）。
- 修复：patch 仅把 pom 属性 `maven-bundle-plugin.version` 4.2.1→5.1.9
  （5.1 修复线最新），OSGi instructions 不变；设备实测 bundle manifest
  正常生成。
- 同域排除：compiler 3.8.1/surefire 3.0.0-M5/jacoco 0.8.5 在 JDK 17 下
  实测正常（目标字节码 Java 8，jacoco 只 instrument Java 8 类文件）。

## 测试口径与门禁

- 口径：`mvn clean package`——test 阶段执行完整上游 JUnit 4.13 套件，
  package 阶段产出 OSGi jar。**jacoco 0.75 覆盖率门绑定在 verify 阶段，
  刻意不进口径**（发布质量门而非库行为；此选择按 Scout 建议记录于此）。
- **计数台账（rule4 复核）**：tag 源码静态 active @Test = 428
  （严格行锚 grep == 宽松出现 grep == 428，0 注释内嵌，0 @Ignore），
  分包 array 51 / monotone 167 / tree 210；59 个测试文件 = 51 个具体套件
  + 8 个抽象基类，JUnit 继承把基类 @Test 带进每个具体子类重跑，故
  surefire 实际执行 **51 套件 / 1391 用例**（rerun-aware 逐
  `<testcase>` 统计，0 failure/0 error/0 skip/0 flaky 记录）。配方
  `_verify_upstream_tests` 按套件数+用例数钉死，MANIFEST 台账给出
  可复算恒等式。
- 上游测试全确定性（`new Random(1)` 固定种子），未用
  `-Dsurefire.rerunFailingTestsCount`，未排除任何用例。
- 设备实测：BiSheng JDK 17.0.13 + Maven 3.8.6，冷缓存（含全量插件下载）
  约 3 分钟，热缓存约 1.5–2 分钟，远低于权威 CI 3600s 默认超时。

## test_package（鸿蒙消费者）

- `test.py` 结构校验：jar 非空/ZIP CRC/全类 major 52/必需条目/精确
  88 class/OSGi `Automatic-Module-Name: org.jheaps`。
- `TestJHeaps.java`（rule12 端到端用例）：64 顶点强连通确定性有向图
  （环 + 固定种子随机边），Dijkstra 分别由 tree `PairingHeap`、array
  `BinaryArrayAddressableHeap`、monotone `DoubleRadixAddressableHeap`
  （受限键域）三族堆驱动，逐一与消费者内 Bellman-Ford 参照互证；
  decreaseKey 句柄复用、键域界、全排空均有断言，合计 200 条。
- 平台差异断言：消费者 JVM 以 `-Dos.name=Linux` 启动（与构建同一归一
  动作），`test.py` 断言其回读 `os.name=Linux`——覆盖 OHOS os.name 特有
  差异在下游消费者侧的真实生效。

## 已知非目标

- jacoco 覆盖率门（verify 绑定）不在验证口径内（见上）。
- 不产出 javadoc/sources jar（release profile 专属，发布用）。
- checkstyle profile 不激活（上游默认关闭）。
