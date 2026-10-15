# TuxGuitar

开源吉他六线谱（Tablature）编辑器与播放引擎。支持多轨、多声部、连音/推弦/泛音等
演奏技法，能读写多种吉他谱格式，并提供乐理工具（音名/八度/调号/音程）与播放序列生成。

- 上游仓库：https://github.com/helge17/tuxguitar
- 许可证：LGPL-2.1-or-later

## 本包内容（鸿蒙 PC 适配范围）

本包适配 TuxGuitar 的**可移植 Java 引擎层**（`libexec/*.jar`），供上层应用/工具调用：

| JAR | 功能 |
|-----|------|
| `tuxguitar-lib` | 核心：歌曲模型、TG 文件格式读写、播放序列、乐理工具、用户目录 |
| `tuxguitar-editor-utils` | 编辑器辅助（连音生成、模板管理） |
| `tuxguitar-gm-utils` | General MIDI 音色/通道工具 |
| `tuxguitar-ascii` | ASCII 谱导出 |
| `tuxguitar-compat` | 旧版格式兼容 |
| `tuxguitar-gtp` / `tuxguitar-gpx` / `tuxguitar-ptb` | Guitar Pro / Power Tab 谱面读写 |
| `tuxguitar-lilypond` | LilyPond 导出 |
| `tuxguitar-midi` / `tuxguitar-pdf` | MIDI 与 PDF 导出 |
| `tuxguitar` / `tuxguitar-ui-toolkit` | 无头应用核心与 UI 抽象层 |

运行期依赖：`commons-compress`、`commons-io`、`commons-lang3`（同置 `libexec/`）。
需 JRE 17+（鸿蒙上为 BiShengJDK 17）。

**不含**：SWT/JFx/Qt GUI 界面与平台原生 MIDI/音频后端（ALSA/JACK/FluidSynth/LV2/winmm/AudioUnit）
—— 这些依赖鸿蒙图形栈/音频子系统的专门移植，不在本包范围。

## 安装与使用

```bash
conan install --requires=tuxguitar/2.0.0 -r=ohpcd
# 产物：<package>/libexec/*.jar
```

## 鸿蒙适配要点

1. **构建层**：上游 `desktop/pom.xml` 仅按 Maven OS family（linux/windows/macos/freebsd）
   激活平台 profile，`os.name=HarmonyOS` 不匹配任何 family，导致 Maven 直接报
   `ProjectBuildingException`。补丁新增 `platform-harmonyos` profile 后可在鸿蒙原生构建。
2. **运行层**：鸿蒙 BiShengJDK 17 的 `user.home` 为不可用的相对占位符（实测字面量 `"?"`），
   会使 TuxGuitar 把配置/缓存目录写到相对当前工作目录的 `"?/.config/tuxguitar"`。
   补丁在对 `user.home` 做绝对路径校验后回退到 POSIX `HOME` 环境变量。
3. **构建子集**：用 Maven 聚合器 `-pl <artifactId,…> -am` 精确构建可移植模块，
   避免拉入 SWT/JNI/android 等平台绑定模块。

## 依赖关系

| 类型 | 依赖 |
|------|------|
| 编译依赖 | 无 Conan 依赖；BiShengJDK 17.0.13 + Apache Maven 3.9.11（配方自取并 sha256 校验） |
| Maven 依赖 | `org.apache.commons:commons-compress:1.26.0`、`commons-io:commons-io:2.15.1`、`org.apache.commons:commons-lang3:3.14.0`（运行期）、`junit-jupiter:5.9.2`（测试期） |

## 状态

| 版本 | 状态 | 上游测试 | test_package |
|------|------|---------|--------------|
| 2.0.0 | built（conan-verify PASS） | 58/58 通过（13 类） | 12/12 通过（含鸿蒙特有 5 例） |
