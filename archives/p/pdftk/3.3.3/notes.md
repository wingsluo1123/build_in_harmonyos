# pdftk 3.3.3 适配笔记

## 上游信息

- **名称**: pdftk（pdftk-java，PDF Toolkit）
- **版本**: 3.3.3（`PDFTK_VER = "3.3.3"`，源码 `java/com/gitlab/pdftk_java/pdftk.java`）
- **仓库**: https://gitlab.com/pdftk-java/pdftk（tag v3.3.3，2022-09-22）
- **许可证**: GPL-2.0-or-later
- **语言**: 纯 Java（`sourceCompatibility = 1.8`），无 native 代码
- **源码包**: `pdftk-v3.3.3.tar.gz`（2380289 字节，sha256 `9c947de5…5b286`）
- **构建系统**: Ant+Ivy 为主（`build.xml` + `ivy.xml`，上游 CI 权威入口），另附 Gradle/Maven 构建
- **主类**: `com.gitlab.pdftk_java.pdftk`（`main_noexit(String[])` 返回进程码，供测试复用）

## 编译环境

- **类型**: 纯 Java CLI 工具（无 native 编译），参照 `archives/j/jakarta-jmeter/2.13` 的 Java 适配链路
- **JDK**: bishengjdk 17.0.13（配方优先 `JAVA_HOME` / `~/bishengjdk17`；HNP 自带的
  `/data/service/hnp/bin/java` 在部分环境启动失败，故不依赖它）
- **Ant**: apache-ant 1.10.15（配方自 archive.apache.org 自取，sha256 `71334d7e…80506` 钉校验；
  经 `sh $ANT_HOME/bin/ant` 调用，规避 HMDFS 对新写文件执行位的限制）
- **Antlib**: Apache Ivy 2.5.2（sha256 `98428d54…eed04`）+ JaCoCo Ant tasks 0.8.4
 （sha256 `d158d4d1…f80e6`），均自 repo1.maven.org 自取，缓存于 `~/.cache-hmbs-pdftk-antlib/`。
  对应上游 CI `apt install ant ivy` 提供的能力（`ant -lib /usr/share/java`）。
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（首轮：配方完整，待真机预检复核）

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/pdftk/3.3.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）

`get()` 下载 GitLab 官方归档 `pdftk-v3.3.3.tar.gz`（sha256 见 conandata.yml），`strip_root=True`。

### 2. 构建（build()）

```bash
sh $ANT_HOME/bin/ant -lib <antlib> main          # clean + ivy resolve + compile + jar
sh $ANT_HOME/bin/ant -lib <antlib> -lib ./lib test-resolve
sh $ANT_HOME/bin/ant -lib <antlib> -lib ./lib test   # 上游 JUnit4 套件（输出存 uptest.log）
```

- `main`：`clean`、`resolve`（ivy 从 Maven Central 按 `ivy.xml` 拉取构建依赖）、
  `compile`（`source/target 1.8`，JDK 17 javac 直接接受，无需补丁）、`jar`
 （`Main-Class: com.gitlab.pdftk_java.pdftk` 的 thin jar）。
- 运行时依赖（ivy build conf，随包发布）：`bcprov-jdk18on-1.71.jar`、
  `commons-lang3-3.12.0.jar`，落盘于源码 `lib/`。
- 测试依赖（ivy test conf，仅构建期）：`junit-4.12.jar`、`system-rules-1.19.0.jar`、
  `org.jacoco.ant-0.8.4.jar` 等。
- 上游测试在 `build()` 内真实运行；`test` 目标的 `<fail if="tests.failed"/>`
  会使 ant 返回非零，配方以 `ignore_errors` 承接并解析 `uptest.log` 中每测试类
  一行的 `Tests run: N, Failures: F, Errors: E, Skipped: S` 汇总（唯一确定性来源），
  生成 `HMBS_UPSTREAM_TEST_RESULT` 标记。断言失败如实记录、不使构建失败；
  无可解析结果（基础设施/依赖失败）则抛错，不吞掉问题。

### 3. 打包（package()）

`libexec/pdftk/` 可运行布局：

- `bin/pdftk.jar`（构建产物）+ `bin/pdftk`（launcher 脚本，由配方写入并 `chmod 755`；
  经 `java -cp "$BIN_DIR/pdftk.jar:$BIN_DIR/../lib/*" com.gitlab.pdftk_java.pdftk` 启动；
  执行位受限环境下可用 `sh bin/pdftk` 调用）
- `lib/`：`bcprov-jdk18on-1.71.jar` + `commons-lang3-3.12.0.jar`（运行时 pdftk 全量需要）
- `licenses/`：LICENSE + README.md + CHANGELOG.md；`share/man/man1/pdftk.1`（上游 man 页）

`package_info()`：`libdirs = ["libexec"]`，`bindirs = ["libexec/pdftk/bin"]`。

## 上游测试（审计 + 接入）

官方 `ant test` 套件（JUnit4，`test/com/gitlab/pdftk_java/`），`BlackBox.java` 为辅助基类：

| 测试类 | @Test 数 | 说明 |
|--------|----------|------|
| AnnotationsTest | 2 | 注解读写 |
| AttachFilesTest | 5 | 附件挂载/导出 |
| BurstTest | 2 | burst 拆页 |
| CatTest | 11 | cat 拼接（8 个经 pdftocairo 比对 SVG） |
| CommandParserTest | 8 | 命令行解析 |
| CryptoTest | 5 | 加解密（2 个经 pdftocairo 比对） |
| DataFieldsTest | 3 | 表单域 |
| DataTest | 14 | dump_data |
| FormTest | 9 | 表单填充 |
| MultipleTest | 2 | 多输入 |
| ReaderTest | 1 | 读取 |
| StampTest | 8 | 水印/图章（2 个经 pdftocairo 比对） |
| **合计** | **70** | 口径：`@Test` 注解数（单一 JUnit4 框架，`upstream_test_count_method: auto`） |

外部工具依赖：`BlackBox.assertPdfEqualsAsSVG` 通过 `Runtime.exec(pdftocairo -svg - -)`
比对 PDF（真机实测 18/70 以 `pdftocairo error` 失败，如 StampTest 8/8；上游 CI 靠
`apt install poppler-utils` 提供）。其余用例无外部进程依赖。真机若缺
`pdftocairo`，相关用例将以 `pdftocairo error` 失败——配方按 rule4 在
`HMBS_UPSTREAM_TEST_RESULT` 中附 `gaps`（environment，计数=失败数，证据为
uptest.log 的 `pdftocairo error` 行 + BlackBox.java 源码定位）。

## test_package（消费者验证，R34）

`test.sh` 三段式（共 12 项，`HMBS_TEST_PACKAGE_RESULT` 计数来自本轮日志的 OK 行）：

1. 结构校验 2 项：`bin/pdftk.jar` 存在；`lib/` 含 `bcprov-jdk18on-1.71.jar` +
   `commons-lang3-3.12.0.jar`。
2. CLI 实跑 1 项：`sh bin/pdftk --version` 报告 `3.3.3`
  （输出首行 `pdftk port to java 3.3.3 …`）。
3. `TestPdftk.java` 9 项断言：pdftk/内嵌 iText `Document` 类存在 →
   `PDFTK_VER=3.3.3` → `main_noexit` 入口存在 → `--version` 返回 0 →
   内嵌 直写最小 1 页 PDF（xref 自算，不经已移除的 PdfWriter.getInstance）（`%PDF-` 头）→ `cat` 返回 0 →
   `cat` 产物为有效非空 PDF → `dump_data` 返回 0 且报告 `NumberOfPages: 1`。
   `javac` 编译成功行为过程输出，不计断言。

## 真机环境注意点

- **HNP 自带 JVM 不可用**：配方与 test_package 均按 `JAVA_HOME` → `~/bishengjdk17`
  顺序解析（与 jakarta-jmeter 同款问题）。
- **HMDFS 执行位**：一律 `sh <script>` 调用 ant/launcher；运行时经 `java -cp` 启动。
- **/tmp EROFS 只读**：测试/构建临时目录用 `mktemp -d` 失败回退 `$HOME`。
- **网络**：构建期需访问 Maven Central（ivy 依赖）与 archive.apache.org（Ant）。
  jakarta-jmeter 在真机实测可达；若本包真机下载超时，按守则补镜像回退。

## 消费者提示

- 命令行：`sh libexec/pdftk/bin/pdftk input.pdf cat output out.pdf`
  （执行位正常时可直接执行 `bin/pdftk`）；`--help` 查看完整操作（cat/burst/
  stamp/fill_form/dump_data/attach_files 等）。
- 适配队伍：龙骑士。


> Round note: PdfWriter.getInstance(Document, OutputStream) does not exist in pdftk-java 3.3.3 (both overloads commented out as ssteward omit in PdfWriter.java); consumer now writes the 1-page input PDF as bytes with computed xref instead of reflection on the removed factory. 9-assertion count unchanged.
