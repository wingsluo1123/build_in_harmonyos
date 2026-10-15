# jakarta-jmeter 2.13

## 软件描述
Apache JMeter 2.13（2015-03 发布）是 Apache 软件基金会的开源负载与性能测试工具：通过测试计划（.jmx）驱动 HTTP/JDBC/JMS/FTP/LDAP/TCP 等采样器做压力测试，支持参数化、断言、监听器与分布式运行；本包面向无头（headless）场景，可经 CLI 运行测试计划。

## 功能概述
- **测试引擎**：`StandardJMeterEngine`、`JMeterContextService`、线程组与调度
- **协议采样器**：HTTP（HttpClient3/4、Java）、JDBC、JMS、FTP、LDAP、SMTP、TCP、Monitors、MongoDB
- **测试计划存取**：`SaveService`（XStream 序列化 .jmx，含版本兼容升级）
- **无头 CLI**：`java -jar ApacheJMeter.jar -n -t plan.jmx -l result.jtl`（GUI 入口同 jar）
- **扩展点**：Function/Assertion/ConfigElement/PreProcessor/PostProcessor 插件体系

## OHOS 适配

### 构建方式
- **纯 Java 应用**（无 native）：官方源码归档 `apache-jmeter-2.13_src.tgz`（archive.apache.org，SHA256 钉校验）+ Ant 构建
  - `ant download_jars`：从 Maven Central 拉取 build.properties 逐 jar 钉 MD5 的运行时依赖（~45 个，含 jorphan/各模块依赖）
  - `ant package`：编译全部模块并组装 bin/ + lib/ + lib/ext/ 可运行布局
  - 产物入 `libexec/jmeter/`：`bin/ApacheJMeter.jar` + 运行时配置 + `lib/*.jar` + `lib/ext/ApacheJMeter_*.jar` + 许可文件
- **工具链自取**（上游无 wrapper）：bishengjdk 17.0.13（cmd-pkgs 路径，优先 `JAVA_HOME`/`~/bishengjdk17`）+ apache-ant 1.10.15（archive.apache.org，sha256 钉校验；经 `sh $ANT_HOME/bin/ant` 调用，规避 HMDFS 新写文件执行位问题）

### 关键点
1. **JDK 17 编译兼容（两个 portability 补丁 + 一处命令行覆盖）**：
   - build.xml 默认 `-source/-target 1.6` 已被 JDK 17 javac 移除——`-Dsrc.java.version=1.8 -Dtarget.java.version=1.8` 命令行覆盖（Ant 命令行属性优先，免 patch）
   - `jm-0001-jdk9-swing-generics.patch`：Swing 自 JDK 9 泛型化（`JTable(Vector,Vector)`→`JTable(Vector<? extends Vector<?>>,Vector<?>)`、`DefaultMutableTreeNode.children()`→`Enumeration<TreeNode>`），2.13 的协变覆写与通配赋值不再合法——5 个文件的最小签名/类型修复
   - `jm-0002-javax-activation-classpath.patch`：`javax.activation` 曾随 JDK 提供（JDK 11 起摘除）——build.xml classpath 增加 `lib/activation-1.1.1.jar` 一行，jar 由配方自 Maven Central 自取（sha256 钉校验 ae475120…4f99），随包发布
2. **HNP 自带 JVM 不可用**：`/data/service/hnp/bin/java` 在部分环境启动即失败（`Failed to mark memory page as executable`）；用 `~/bishengjdk17`（BiSheng JDK 17.0.13）
3. **运行期 JVM 旗标**：老 xstream 1.4.8 在 JDK 17 需 `--add-opens=java.base/java.util=ALL-UNNAMED`（等）才能反射访问 JDK 集合字段——无头 CLI 跑 `-n -t` 测试计划（不用 SaveService 反序列化旧格式或加旗标前）可正常运行；消费 `.jmx` 时需注意
4. **上游测试如实披露**：官方无头套件 `ant test-headless` 真机实测 1596 用例，1475 通过 / 1 失败 / 120 错误（92.4%）。失败集中在三类 2015 年代码/依赖与 JDK 17 的时代差异（xstream JPMS 反射、headless 字体栈、htmlparser compact-strings 假设），详见 notes.md 失败清单；batchtest（golden diff）属 `ant test` 目标，本轮未运行

### 与 Linux 的差异
无本质差异——纯 Java（aarch64 JVM 字节码一致）。差异仅来自运行环境：headless 字体栈初始化失败影响 GUI 类测试与监听器（服务器级 Linux 通常带 fontconfig，本设备无）。

## 依赖关系
- **构建期**：bishengjdk 17.0.13 + apache-ant 1.10.15（配方自取，不产生 Conan 依赖）；Maven Central（download_jars，MD5 钉）+ javax.activation:activation 1.1.1（配方自取，sha256 钉）
- **运行期**：JDK 8+ JVM（建议 17 并按需加 --add-opens）；libexec/jmeter/lib 内已含全部运行时 jar

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 2.13 | built | 2026-10-13 | 源码编译全模块；libexec/jmeter 可运行布局；上游测试 92.4%（1475/1596）如实记录 |

## 参考资料
- 官方主页: https://jmeter.apache.org/
- 2.13 归档: https://archive.apache.org/dist/jmeter/source/apache-jmeter-2.13_src.tgz
- 2.13 变更: https://jmeter.apache.org/changes_2.13.html
