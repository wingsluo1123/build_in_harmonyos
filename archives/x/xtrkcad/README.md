# xtrkcad

XTrackCAD —— 模型铁路线路设计 CAD 程序（GTK2 图形界面，C + CMake）。

- 上游：<https://xtrkcad-fork.sourceforge.net/>
- 源码：SourceForge `xtrkcad-fork` 发布包 `xtrkcad-source-5.3.1GA.tar.gz`（sha256 `5b02a035…572c`）
- 许可：GPL-2.0-or-later
- 构建系统：CMake（Ninja 后端）

## OpenHarmony PC 适配要点

| 问题 | 对策 |
|------|------|
| HarmonyOS 不是 CMake 已知系统名 → `UNIX` 为假，工程走非 POSIX 分支（`configure` 因缺 `Libzip::Libzip` 目标失败） | 源码补丁按 **Unix 类平台**处理（`CMAKE_SYSTEM_NAME` 为 `HarmonyOS`/`OHOS` 时 `set(UNIX 1)`），**不伪装 `CMAKE_SYSTEM_NAME`**（见知识条目 E092） |
| 上游用 Inkscape 把工具条 SVG 图标转成位图头文件，鸿蒙侧无 inkscape | 用制品仓 `librsvg` 静态库自建 `svg2png`（随包发布到 `bin/`），接受与 Inkscape 相同的命令行形态（`INPUT.svg -h N -o OUT.png`），由 `CMake/FindInkscape.cmake` 找到 |
| Conan `CMakeDeps` 生成小写导入目标，工程 `CMake/Find*.cmake` 用大写变量 | 顶层 `CMakeLists.txt` 双向桥接 |
| `app/bin/bitmaps/CMakeLists.txt` 为 CRLF 文件，补丁管线（文本模式读取）无法套用 LF 补丁 | 适配版本放在 `ohos/bitmaps/`，经 `exports_sources` 交付，构建时覆盖 |
| `gtk/gtkunixprint.h` 找不到（conan 包内无对应 `.pc` wrapper） | `FindGTKUnixPrint.cmake` 改为按头文件实际存在性判定（能力探针） |

## 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| gtk2 | 2.24.33 | GUI（UNIX 默认 `XTRKCAD_USE_GTK=ON`） |
| libzip | 1.11.4 | 布局文件压缩容器 |
| librsvg | 2.62.3.1.1 | 构建期 SVG 光栅化（`svg2png`，替代 Inkscape） |
| cmocka | 2.0.2 | `test_requires`，上游单测框架 |

## 构建

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 验证

- 本地全量构建：`cmake --build` 128 个目标全绿，`failed=0`
- 上游测试：`ctest --output-on-failure` → **5/5 通过**（24 个可运行 cmocka case；上游活跃 26 个，第 6 个注册项 `UTF8ConversionTest` 位于 `app/wlib/mswlib/`，MSW 专用，本平台不参与构建）
- 包测试：链接包内 `libdynstring.a` 的消费者用例实跑通过；`svg2png` 实跑产出合法 PNG（`89 50 4e 47 0d 0a 1a 0a`）

> GUI 运行时需要 X 服务器，鸿蒙 PC 不提供，故验证止于编译/链接层 + 上游 ctest + 包内工具实跑。
> R40：图形/UI 类库需人工复核适配完整性——本包无 stub/占位实现（改动集中在平台判定与能力探测），X 服务器依赖已如实披露，建议合入前人工确认。
