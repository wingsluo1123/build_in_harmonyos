# jtreg7 7.5.2-1 鸿蒙系统适配指南

> **版本**: 1.0 | **更新日期**: 2026-10-14 | **状态**: ✅ 已验证

## 概述

| 项目 | 信息 |
|------|------|
| 软件版本 | jtreg 7.5.2+1（Conan 引用 `jtreg7/7.5.2-1`） |
| 目标平台 | HarmonyOS PC aarch64 (musl libc, HongMeng Kernel 1.12) |
| 上游仓库 | https://github.com/openjdk/jtreg |
| 运行时依赖 | BiShengJDK 17+（构建时经 cmd-pkgs 自动安装，运行测试需要 JDK） |
| 构建依赖 | GNU make、Ant 1.10.8（配方自取缓存）、JT Harness / AsmTools / JUnit / TestNG（上游 build.sh 自动下载并校验） |
| 适配复杂度 | 🟢 低（1 个可移植性补丁：`make/Platform.gmk` 识别 HarmonyOS） |

## 快速开始

```bash
# 1. 安装（Conan 制品仓, 需先登录）；构建时会自动准备 BiShengJDK 17
conan install --requires=jtreg7/7.5.2-1

# 2. 定位包目录
PKG=$(conan cache path jtreg7/7.5.2-1)

# 3. 运行自检
sh "$PKG/bin/jtreg" -version

# 4. 运行一个 JDK 回归测试套件（示例）
sh "$PKG/bin/jtreg" -jdk:$JAVA_HOME -w /tmp/jtwork -r /tmp/jtreport /path/to/test/suite
```

## 适配要点

1. **平台识别补丁（唯一补丁）**：上游 `make/Platform.gmk` 仅识别
   SunOS/Linux/FreeBSD/Darwin；HarmonyOS 的 `uname -s` 返回 `HarmonyOS`，
   会落入 Windows 分支，使类路径分隔符 `PS` 变成分号（`;`），javac 在
   `-Werror` 下因 `[path] bad path element` 直接失败。补丁为 HarmonyOS
   增加与 Linux 相同的分支（`archives/j/jtreg7/7.5.2-1/patches/0001-*.patch`）。
   真机微探针实证：补丁前 `OS_NAME=windows PS=;`，补丁后 `OS_NAME=linux PS=:`。
2. **构建工具链**：上游 `make/build.sh` 自行下载 Ant、JT Harness、AsmTools、
   JUnit 5 platform、TestNG 并做校验和验证；配方做了三处网络适配：
   - Ant 由配方预取并缓存到 `~/apache-ant-1.10.8`，经 `ANT` 环境变量传入；
   - Maven 依赖走阿里云 central 镜像（CI 直连 repo1.maven.org 会重置）；
   - TestNG LICENSE 从 GitHub 上的 testng 源码 tarball 提取（sha1 钉校验），
     因为 `raw.githubusercontent.com` 不可达；设备上 toybox wget 不支持 `-q`，
     配方在 curl 可用时生成 wget→curl shim。
3. **JDK**：构建与运行都需要 JDK 17+（BiShengJDK 17.0.13）。配方在 JAVA_HOME
   缺失时经 cmd-pkgs 自动安装到 `~/bishengjdk17`（纯进程内 conan download +
   tarfile 解压，规避 CI worker 沙箱的 fork 限制）。
4. **JDK 版本代差注意（与同族 6.2 的差异实证）**：jtreg 6.2 需额外排除
   `removal` lint（`-Xlint:all -Werror` 在 JDK 17 下被 Applet forRemoval 触发）；
   **7.5.2 的 `make/Defs.gmk` 使用 `--release 8/11`**，旧 API 视图屏蔽了
   removal 警告，无需该补丁——仅为 Platform.gmk 单补丁。

## 验证

- 真机构建 + 上游 `quick-test`（HEADLESS=1）通过（`All (10) selected tests
  completed successfully`）；完整上游自测套件在真机运行（见
  `7.5.2-1/notes.md` 与 `7.5.2-1/reports/test-report.md` 的逐项结论）。
- `test_package`：用打包的 jtreg 运行一个含"故意失败"用例的迷你 JDK 测试套件，
  校验通过/失败统计与报告内容（12 项断言）。

## 已知限制

- 与同族版本一致的平台语义差异（详见 `7.5.2-1/reports/test-report.md`）：
  鸿蒙 chmod 只读语义受限（CleanupTests.retain）、JVM `os.version` 含空格
  （ProblemList OSNAME-REV 选择器失配）、toybox grep 不支持 BRE `\+`
  （SkippedExceptionTest 的 summary 断言）。以上均为平台/工具差异，
  对应 jtreg 用例本身按预期运行，不影响 jtreg 正常功能。
