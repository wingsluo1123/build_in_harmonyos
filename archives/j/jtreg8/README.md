# jtreg8 8.3-1 鸿蒙系统适配指南

> **版本**: 1.0 | **更新日期**: 2026-10-04 | **状态**: ✅ 已验证

## 概述

| 项目 | 信息 |
|------|------|
| 软件版本 | jtreg 8.3+1（Conan 引用 `jtreg8/8.3-1`） |
| 目标平台 | HarmonyOS PC aarch64 (musl libc, HongMeng Kernel 1.12) |
| 上游仓库 | https://github.com/openjdk/jtreg |
| 运行时依赖 | BiShengJDK 17+（构建时经 cmd-pkgs 自动安装，运行测试需要 JDK） |
| 构建依赖 | GNU make、Ant 1.10.15（配方自取缓存）、JT Harness / AsmTools / JUnit / TestNG（上游 build.sh 自动下载并校验） |
| 适配复杂度 | 🟢 低（1 个可移植性补丁：`make/Platform.gmk` 识别 HarmonyOS） |

## 快速开始

```bash
# 1. 安装（Conan 制品仓, 需先登录）；构建时会自动准备 BiShengJDK 17
conan install --requires=jtreg8/8.3-1

# 2. 定位包目录
PKG=$(conan cache path jtreg8/8.3-1)

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
   增加与 Linux 相同的分支（`archives/j/jtreg8/8.3-1/patches/0001-*.patch`）。
2. **构建工具链**：上游 `make/build.sh` 自行下载 Ant、JT Harness、AsmTools、
   JUnit、TestNG 并做校验和验证；配方做了三处网络适配：
   - Ant 由配方预取并缓存到 `~/apache-ant-1.10.15`，经 `ANT` 环境变量传入；
   - Maven 依赖走阿里云 central 镜像（CI 直连 repo1.maven.org 会重置）；
   - TestNG LICENSE 从 GitHub 上的 testng 源码 tarball 提取（sha1 钉校验），
     因为 `raw.githubusercontent.com` 不可达；设备上 toybox wget 不支持 `-q`，
     配方在 curl 可用时生成 wget→curl shim。
3. **JDK**：构建与运行都需要 JDK 17+（BiShengJDK 17.0.13）。配方在 JAVA_HOME
   缺失时经 cmd-pkgs 自动安装到 `~/bishengjdk17`。

## 验证

- 真机构建 + 上游 `quick-test` 9/9 通过；完整上游自测套件在真机运行（见
  `8.3-1/notes.md` 的逐项结论，其中 1 项涉及鸿蒙文件权限语义差异）。
- `test_package`：用打包的 jtreg 运行一个含"故意失败"用例的迷你 JDK 测试套件，
  校验通过/失败统计与报告内容（12 项断言）。

## 已知限制

- `test/cleanup` 自测中的 `CleanupTests.agentvm.retain` 依赖"只读目录让文件不可
  删除"的 POSIX 权限语义；鸿蒙文件系统/SELinux 下 chmod 受限，jtreg 能正常清理
  并复用 scratch 目录，导致该目标断言失败（5 个用例本身全部 PASS）。不影响
  jtreg 正常功能。
