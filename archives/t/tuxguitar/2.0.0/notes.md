# tuxguitar 2.0.0 — 鸿蒙 PC 适配笔记

## 项目信息

- **软件**: TuxGuitar —— 吉他六线谱（Tablature）编辑/播放引擎
- **版本**: 2.0.0
- **上游**: https://github.com/helge17/tuxguitar （tag `2.0.0`，commit `1190aa2b063c8e441600d2c334c9798256528c7a`）
- **许可证**: LGPL-2.1-or-later
- **语言**: Java（源码统计 2680 个文件，java 2650 个，主体占比 99%）
- **构建系统**: Maven 多模块（76 个 `pom.xml` + android 子树的 Gradle）
- **目标平台**: HarmonyOS PC（aarch64，BiShengJDK 17.0.13）

## 适配范围与取舍

TuxGuitar 是一个 Java 桌面应用（SWT/JFx/Qt 三种 GUI toolkit + 平台原生 MIDI 后端）。
鸿蒙 PC 不提供 SWT 所需的 X11/GTK 运行栈，也没有上游 `jni/` 目标里的 ALSA/JACK/FluidSynth/
AudioUnit/winmm 等原生库，因此本包**只适配其可移植的 Java 引擎层**（这也是 TuxGuitar 的
核心价值所在：`app.tuxguitar.song.*` 歌曲模型、`io.tg/gp*/ptb` 文件格式、播放序列与乐理工具）：

| 构建 | 说明 |
|------|------|
| `common/TuxGuitar-lib` | 核心库（歌曲模型、TG 文件格式读写、播放序列、乐理工具、用户目录） |
| `common/TuxGuitar-{gm-utils,editor-utils,ascii,compat,gtp,gpx,lilypond,midi,ptb,pdf}` | 10 个可移植功能模块 |
| `desktop/TuxGuitar`、`desktop/TuxGuitar-ui-toolkit` | 无头应用核心与 UI 抽象层（被 `-am` 带入） |
| 排除 | `*-ui-toolkit-{swt,jfx,qt}`、`TuxGuitar-{alsa,jack,fluidsynth,AudioUnit,winmm,synth-lv2}/jni`、`android/` |

产物：16 个 JAR 置于 `libexec/`（13 个 TuxGuitar 模块 JAR + 3 个运行期依赖
`commons-compress-1.26.0`、`commons-io-2.15.1`、`commons-lang3-3.14.0`），库类型包，无入口脚本。

## 编译环境

- **JDK**: BiShengJDK 17.0.13（`~/bishengjdk17`，`JAVA_HOME` 优先，缺失时经 cmd-pkgs 自动安装）
- **Maven**: apache-maven 3.9.11（配方从 `repo1.maven.org` 自取并以 sha256 校验，上游无 mvnw）
- **网络**: Maven Central 经阿里云 central 镜像（`maven.aliyun.com`），失败重试 3 次后直连兜底
- **聚合器**: `desktop/build-scripts/tuxguitar-linux-swt`（唯一携带 common 模块的 reactor）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `mvn` 在鸿蒙上直接失败：`'dependencyManagement.dependencies.dependency.groupId' for ${org.eclipse.swt.groupId}:org.eclipse.swt.gtk.linux ... does not match a valid id pattern` → `The build could not read 1 project`（ProjectBuildingException） | `desktop/pom.xml` 只在按 Maven **OS family** 激活的 profile 里定义 `org.eclipse.swt.groupId/artifactId`；profile 激活条件是 `family=unix&name=linux` / `windows` / `mac os x` / `freebsd`。鸿蒙 `os.name=HarmonyOS`，既不属 unix 也不属 windows —— 没有任何 profile 激活，属性未解析，Maven 在读取 POM 阶段即中止 | **补丁 0002**：新增 `<os><name>HarmonyOS</name></os>` 激活的 `platform-harmonyos` profile，补齐同款属性（与上游 freebsd profile 结构一致）。修复后 `os.name=HarmonyOS` 下原生 `mvn` 直接 BUILD SUCCESS |
| 2 | `TGUserFileUtils.PATH_USER_DIR` 被解析为相对路径 `?/.config/tuxguitar`，并在当前工作目录真实创建出名为 `?` 的目录 | 鸿蒙 BiShengJDK 17 把系统属性 `user.home` 报告为**字面量 `"?"`**（长度 1、`isAbsolute()==false`），而 `getDefaultUserAppDir()` 直接 `new File(home)` 拼接，相对路径按 CWD 解析 | **补丁 0001**：新增 `getUsableUserHome()`——`user.home` 不是可用绝对路径时回退到 POSIX `HOME` 环境变量（unix 系平台恒为绝对路径），再不行才原样返回。`user.home` 正常的平台（Linux/Windows/macOS）行为完全不变 |
| 3 | — | 验证环境自检：确认 3 个问题均非本地误配（`os.name`/`user.home`/`HOME` 用独立 Java 探针实测） | 探针输出：`os.name=HarmonyOS`、`user.home len=1 cps=U+003F`、`env HOME=/storage/Users/currentUser` |

> 上游源码里另一处 `os.name` 分支 `TGUserFileUtils.getDefaultUserAppDir()` 的 macOS/Windows
> 判断本身对鸿蒙是安全的（落到可移植的 `~/.config` 分支），因此**未改动**；本次只修
> "home 取值不可靠"这一个真实缺陷（最小改动，R1）。

## 上游测试

- 上游为 JUnit 5.9.2 + Maven Surefire，随 `mvn package` 自动执行，**无独立测试入口脚本**
  （`.github/workflows` 即 `mvn -e clean verify -P native-modules`）。
- 清点：`src/test/java` 下 13 个测试类（`grep -rn "@Test"` 计 58 个用例）；
  覆盖 `common/TuxGuitar-lib`（11 类 56 例）、`common/TuxGuitar-editor-utils`（1 类 1 例）、
  `common/TuxGuitar-compat`（1 类 1 例）。
- 实测：**58 / 58 通过，0 失败 0 错误 0 跳过**（无跳过项，无漏测：`discovered == executed == passed == 58`）。
  逐类逐例名称见 `test_package/MANIFEST.yml` 与 `reports/conan-create.log`
  （`HMBS_UPSTREAM_TEST_RESULT={"discovered":58,"executed":58,"passed":58,"failed":0,"errors":0,"skipped":0,"classes":13}`）。
- 鸿蒙特有测试：**5 例**（`test_package/TestHarmonyOSPlatform.java`，见下）。
- test_package 消费者测试：12 例（7 核心 + 5 鸿蒙），全部 PASS。

## test_package 测试（消费者视角，鸿蒙真机运行）

`test.sh` 用 `javac` 编译两个 Java 消费者程序并 `java` 运行，断言 JAR 由 `libexec/` 实际加载：

1. `TestTuxGuitarCore` —— 7 例：版本解析 / 打包版本确为 2.0.0 / 版本排序 /
   `TGSongManager.newSong()` 默认结构 / 默认 6 弦 / 经 `TGMeasureManager.addNote` 写入并回读音符 /
   `TGMusicKeyUtils` MIDI 69 → A4。
2. `TestHarmonyOSPlatform` —— **5 例（鸿蒙特有）**：
   - `ohos.osNameIsHarmonyOS`：JVM 实报 `os.name=HarmonyOS`；
   - `ohos.userDirUsesPortableBranch`：用户目录走可移植 `~/.config/tuxguitar` 分支；
   - `ohos.userDirIsAbsolute`：目录为绝对路径（针对 `user.home="?"` 的回归护栏）；
   - `ohos.userDirUnderHome`：目录位于 `$HOME` 之下；
   - `ohos.userDirWritable`：目录真实可写（建/删探针文件）。

## 验证结果

```bash
# 上游构建 + 上游测试（真实命令，见 reports/conan-create.log）
$ mvn -B -pl :tuxguitar-lib,:tuxguitar-gm-utils,:tuxguitar-editor-utils,:tuxguitar-ascii,:tuxguitar-compat,:tuxguitar-gtp,:tuxguitar-gpx,:tuxguitar-lilypond,:tuxguitar-midi,:tuxguitar-ptb,:tuxguitar-pdf -am clean package
[INFO] Tests run: 56, Failures: 0, Errors: 0, Skipped: 0     # TuxGuitar-lib
[INFO] Tests run: 1,  Failures: 0, Errors: 0, Skipped: 0     # TuxGuitar-editor-utils
[INFO] Tests run: 1,  Failures: 0, Errors: 0, Skipped: 0     # TuxGuitar-compat
[INFO] BUILD SUCCESS

# conan-verify（profile: ci/conan/profiles/ohos-aarch64）
$ python3 scripts/ohc-run.py conan-verify tuxguitar 2.0.0
G0 ✅ PASS / G1 ✅ PASS / G2 ✅ PASS (conan create) / G3 ✅ PASS / G4 ✅ PASS / L2·L4·L5 跳过（纯 JAR 包无 cache 路径）
Verdict: PASS（conan-verify 全绿，产物具备发布条件）
```

## 交付物

- `conanfile.py` / `conandata.yml` / `patches/`（2 个）/ `test_package/`（5 个）
- `manifest.yaml` / `notes.md` / `reports/conan-verify-report.md`、`reports/conan-create.log`
- 包内容：`libexec/*.jar`（16）、`libexec/upstream-test-result.json`、`licenses/LICENSE`

## 后续（未纳入本 PR）

- GUI 层（SWT/JFx/Qt）需要鸿蒙图形栈移植，非本包范围。
- 平台原生 MIDI/音频后端（ALSA/JACK/FluidSynth/LV2/winmm/AudioUnit）需针对 OHOS 音频子系统重写。
---

**编译结束**: 2026-10-14 14:49
**最终状态**: built
