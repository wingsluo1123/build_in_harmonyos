# pdftk 3.3.3

## 简介

pdftk-java 3.3.3（PDF Toolkit）：操作 PDF 的命令行工具——`cat` 拼接、`burst` 按页拆分、
`stamp`/`background` 水印、`fill_form` 表单填充、`dump_data`/`update_info` 元数据读写、
`attach_files` 附件、`input_pw` 解密等。纯 Java 实现（内嵌 iText），上游仓库
<https://gitlab.com/pdftk-java/pdftk>，许可证 GPL-2.0-or-later。

## OHOS 适配

### 打包形式

- **纯 Java 应用**，无 native 编译；GitLab 官方归档 `pdftk-v3.3.3.tar.gz`（SHA256 校验）+ Ant 构建
  - `ant main`：clean + ivy resolve + 编译（`source/target 1.8`，JDK 17 直接接受）+ 组装 `pdftk.jar`
  - `ant test`：上游 JUnit4 套件（70 个用例）在 `build()` 内真实运行
- **依赖自取**（构建期脚本）：bishengjdk 17.0.13（cmd-pkgs；`JAVA_HOME`/`~/bishengjdk17`）+
  apache-ant 1.10.15（archive.apache.org，sha256 钉校验）+ ivy/jacoco 任务 jar
 （Maven Central，sha256 钉校验）；一律 `sh` 调用，规避 HMDFS 新写文件执行位限制
- **产物**：`libexec/pdftk/`（`bin/pdftk.jar` + `bin/pdftk` launcher + `lib/` 运行时 jar）

### 关键点

1. **零补丁**：JDK 17 可直接编译 `source/target 1.8` 的上游源码；`patches/` 为空。
2. **上游测试全接入**：12 个 JUnit 类 / 70 个 `@Test`，结果由框架输出解析；
   其中 12 个 SVG 比对用例需外部 `pdftocairo`（poppler），缺失时如实记环境缺口。
3. **消费者验证**：`--version` 实跑 + 内嵌 iText 建 PDF + `cat`/`dump_data` 端到端（12 项）。

## 使用

```sh
sh libexec/pdftk/bin/pdftk input.pdf cat output out.pdf
sh libexec/pdftk/bin/pdftk out.pdf dump_data
sh libexec/pdftk/bin/pdftk --help
```
