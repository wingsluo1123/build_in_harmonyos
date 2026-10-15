# jakarta-jmeter 2.13 适配笔记

## 编译环境
- **类型**: 纯 Java 应用（无 native 编译）
- **编译日期**: 2026-10-13
- **JDK**: bishengjdk 17.0.13（配方优先 `JAVA_HOME` / `~/bishengjdk17`；**HNP 自带的
  `/data/service/hnp/bin/java` 在本环境启动失败**——`Error occurred during initialization
  of VM` / `Failed to mark memory page as executable`，见 jakarta-activation notes 同款问题）
- **Ant**: apache-ant 1.10.15（配方自 archive.apache.org 自取，sha256 `71334d7e…80506` 钉校验；
  经 `sh $ANT_HOME/bin/ant` 调用，规避 HMDFS 对新写文件执行位的限制）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/j/jakarta-jmeter/2.13 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 下载 `apache-jmeter-2.13_src.tgz`（archive.apache.org 官方归档，sha256
`f5aeda5d…957f`，与官方 .md5 一致），`strip_root=True`。

### 2. 构建（build()）
```bash
sh $ANT_HOME/bin/ant -Dsrc.java.version=1.8 -Dtarget.java.version=1.8 download_jars package
```
- `download_jars`：从 Maven Central（repo1.maven.org）拉取 build.properties 逐 jar 钉
  MD5 的运行时依赖（~45 个 jar；真机网络实测可达）
- `package`：编译 jorphan/core/components/functions/protocols/monitor/junit/jms/native/
  mongodb 全部模块，组装 `bin/ApacheJMeter.jar` + `lib/*.jar` + `lib/ext/ApacheJMeter_*.jar`
- **JDK 17 覆盖**：build.xml 默认 `-source/-target 1.6` 在 JDK 17 javac 已移除；Ant 命令行
  `-D` 属性优先级高于 build.xml `<property>`，免 patch 覆盖为 1.8
- 构建前配方先把 `activation-1.1.1.jar`（sha256 钉 `ae475120…4f99`）取到 `lib/`——
  `javax.activation` 自 JDK 11 起摘除，2015 年源码默认 JDK 自带（见补丁 2）

### 3. 打包（package()）
`libexec/jmeter/` 可运行 JMeter home 布局：
- `bin/`：ApacheJMeter.jar + 运行时配置（*.properties/*.conf/*.xml/*.parameters/*.bshrc；
  排除启动脚本/testfiles/examples/templates）
- `lib/`：download_jars 拉取的第三方 jar + activation-1.1.1.jar（运行时 NewDriver 全量装载）
- `lib/ext/`：ApacheJMeter_*.jar（15 个模块 jar）
- `LICENSE`/`NOTICE`/`README` + `licenses/`
`package_info()`：`libdirs = ["libexec"]`。

## 补丁说明（全部 portability 性质，最小可解释）

1. **`jm-0001-jdk9-swing-generics.patch`**（5 文件，均为泛型签名）
   - `JTreeTable(Vector<?>,Vector<?>)` 构造调用 `super(rowData,columnNames)`：JDK 9 起
     JTable 构造改为 `(Vector<? extends Vector<?>>,Vector<?>)`，捕获类型不匹配 →
     原生类型双转型（老 raw 构造仍在，仅 unchecked 警告）
   - `JMeterTreeNode.children()` 返回 `Enumeration<JMeterTreeNode>`：JDK 9 起
     `DefaultMutableTreeNode.children()` 返回 `Enumeration<TreeNode>`，协变覆写非法 →
     改返回 `Enumeration<TreeNode>`，5 处调用点经 `(Enumeration<?>)` 通配双转型保持语义
2. **`jm-0002-javax-activation-classpath.patch`**（build.xml 1 行）
   - `javax.activation` 包曾随 JDK 提供，JDK 11 起摘除；SMTP 采样器
     （src/protocol/mail/SendMailCommand）编译需要——classpath 增补
     `lib/activation-1.1.1.jar`；jar 由配方自取并随包发布

## 上游测试（真实运行，如实记录）

官方无头入口 `ant test-headless`（`org.apache.jorphan.test.AllTests` 汇集 JUnit 单测），
在设备上原样运行（与 CI 外验证步骤同源，非 conan build() 内）：

| 项 | 值 |
|----|----|
| 用例总数 | **1596** |
| 通过 | **1475（92.4%）** |
| 失败 | **1**（TestMenuFactory.testMenu——菜单工厂断言，依赖 AWT/字体） |
| 错误 | **120** |
| batchtest | **未运行**（属 `ant test` 目标，非 test-headless；如实记为未覆盖，非 PASS） |

错误按根因分类（完整清单见 `upstream-tests/failure-list-run1.txt`）：

| 根因 | 数量 | 说明 |
|------|------|------|
| SaveService/xstream 初始化失败 | 65 | xstream 1.4.8（build.properties 钉 MD5）在 JDK 17 触发 JPMS `InaccessibleObjectException`：`--add-opens` 逐层暴露 java.util→java.lang.reflect→java.awt.font，两轮旗标集合均未收敛（诊断日志 rerun-add-opens.log / rerun2-add-opens.log）——消费 .jmx 的运行期依赖，属上游依赖决策（旗标集合或升级 xstream），不在本 run 内代做 |
| headless 字体栈失败 | 15 | 真实根因 `UnsatisfiedLinkError: libfontmanager.so` 缺 `libfreetype.so.6`（设备 JDK 依赖缺口）——GUI/菜单/bean 编辑器/可视化器类测试在此环境无法通过 |
| htmlparser 2.1 [B→[C | 33 | 2006 年代 htmlparser 假设 String 内部表示，JDK 9+ compact strings 下 `ClassCastException: [B cannot be cast to [C` |
| ProxyControl 初始化连带 | 7 | 类初始化依赖上述链条（ExceptionInInitializerError + NoClassDefFoundError 连锁） |

**结论**：92.4% 通过率反映的是 2015 年代码/依赖与 JDK 17、无字体 headless 环境的时代
差异，而非移植缺陷（工程构建产物被 test_package 的实跑验证覆盖）。是否将上述三类失败
视为门禁缺口，由 Coordinator 汇报用户决定。

## 真机环境注意点
- **HNP 自带 JVM 不可用**：`/data/service/hnp/bin/java` 启动即失败——配方与 test_package
  均按 `JAVA_HOME` → `~/bishengjdk17` 顺序解析
- **HMDFS 执行位**：home 下新写脚本可能无执行位——一律 `sh <script>` 调用 ant；
  JMeter 运行时经 `java -jar`/`java -cp` 启动，不依赖脚本执行位
- **/tmp EROFS 只读**：测试/构建临时目录避开 /tmp（mktemp 失败回退 $HOME）

## 消费者提示
- CLI 跑测试计划：`java -jar libexec/jmeter/bin/ApacheJMeter.jar -n -t plan.jmx -l out.jtl`
  （GUI 同 jar，需显示环境）
- JDK 17 下读写旧格式 .jmx（SaveService/xstream）需评估 `--add-opens` 集合或升级
  xstream——见上游测试根因 1
