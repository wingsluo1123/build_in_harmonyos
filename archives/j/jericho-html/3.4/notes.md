# jericho-html 3.4 适配笔记

## 软件概况
- Jericho HTML Parser 3.4（2015-10-24 上游最终官方版），纯 Java HTML 解析库
- Maven 坐标：net.htmlparser.jericho:jericho-html:3.4
- 三重许可：EPL-1.0 / LGPL-2.1 / Apache-2.0（任选其一）
- 运行时零依赖（slf4j/commons-logging/log4j-api 均为 optional）

## 适配方式
- 源码：Maven Central 官方 sources.jar（仅主源码，无测试）
- 编译：javac（JDK 17，-source 7 -target 7 对应上游 POM）+ jar 打包
- 测试：上游 JUnit 4.8.2 测试套件（SourceForge 项目包 test/src/ 完整 vendored 至 upstream-tests/），build() 中 javac 编译后 JUnitCore 运行 TestSuite
- JDK：复用 jackson-core 同款 _ensure_java()，CI 无 JDK 时自动通过 cmd-pkgs 安装 bishengjdk 17.0.13

## 上游测试规模
- 14 个测试类：TestSuite 聚合 13 个（含 samples 的 HTMLSanitiserTest）+ StAXTest（上游整类注释，需 JDK 1.6 StAX，跳过编译）
- 可运行 @Test：50 个（StreamedSourceHugeFileTest 2 个用例上游自带 `if (true) return;` 禁用，计入运行且通过）
- 上游测试零修改：仅排除上游自身注释掉的 StAXTest.java

## 网络环境备忘（2026-10-13）
- sourceforge.net / downloads.sourceforge.net 全部镜像（master/deac-riga/phoenixnap 等）在本环境连接被拒
- api.github.com 不可达；gitee 无镜像
- 测试源码来源：Debian salsa 仓库（java-team/jericho-html，upstream/3.4+dfsg 导入自 SourceForge 官方 zip，仅去除非自由文件，test/src 完整）
---

**编译结束**: 2026-10-13 22:26
**最终状态**: published
