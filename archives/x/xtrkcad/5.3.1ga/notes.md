# xtrkcad 5.3.1ga 适配笔记

## 编译环境
- 构建系统: cmake（`CMakeLists.txt`，`cmake_minimum_required(VERSION 3.20.0)`，UNIX 下 `pkg_check_modules(GTK REQUIRED "gtk+-2.0")`）
- 上游版本: XTrkCad 5.3.1GA（SourceForge `xtrkcad-fork` 官方发布；conan 包版本归一为小写 `5.3.1ga` 以匹配任务分支）
- 源码 URL: https://downloads.sourceforge.net/project/xtrkcad-fork/XTrackCad/Version%205.3.1/xtrkcad-source-5.3.1GA.tar.gz
- 源码规模: 246 个 `.c` + 头文件（GUI CAD 应用）
- 编译日期: 2026-10-01
- 编译器: clang/clang++（OHOS aarch64）
- 状态: 构建通过（cmake 128/128 全绿 + 上游 ctest 5/5；W3 `conan create` 验证见下）

## 上游测试申报表（R51 三步法 · 步骤1 清点）

清点证据（在源码根执行）：
```bash
grep -rn "add_test" --include=CMakeLists.txt .        # 7 处，其中 1 处被上游注释
grep -rh "cmocka_unit_test" app/ | wc -l              # 34（含被禁用的 catalogtest 8）
```

| 测试类型 | 上游用例数 | 说明（来源证据） |
|----------|-----------|------|
| 单元测试（ctest 注册目标） | **6** | `add_test` 生效 6 处；`app/bin/unittest/CMakeLists.txt:57` 的 `CatalogTest` 被上游注释禁用（"pulls in too many dependencies"） |
| 单元测试（cmocka case） | **26 活跃**（34 含禁用组） | `cmocka_unit_test` 宏计数：shortentest 8、dxfformattest 6、catalogtest 8（禁用）、pathstest 2、defaultstest 2、DynStringTest 6、utf8test 2 |
| 手工测试程序 | `app/wlib/test/*` | alarmtst/boxtest/btest/colortst/draw 等，仅 Win32 `.mak` 工程，未注册 ctest（非 CI 可跑） |
| **合计（本平台可运行）** | **5 个测试目标 / 24 个 case** | 上游活跃 26 个 case 含 2 个 MSW 专用（utf8test） |

ctest 注册明细：

| ctest 名 | 目标 | 源文件 | case |
|---|---|---|---|
| DXFOutputTest | dxfformattest | `app/bin/unittest/dxfformattest.c` + `../dxfformat.c` | 6 |
| PathsTest | pathstest | `app/bin/unittest/pathstest.c` | 2 |
| DefaultsTest | defaultstest | `app/bin/unittest/defaultstest.c` | 2 |
| ShortenTest | shortentest | `app/bin/unittest/shortentest.c` + `../shortentext.c` | 8 |
| UTF8ConversionTest | utf8test | `app/wlib/mswlib/unittest/utf8test.c` | 2 |
| DynStringTest | dynstringtest | `app/dynstring/unittest/DynStringTest.c` | 6 |
| ~~CatalogTest~~ | catalogtest | 上游第 57 行注释禁用 | (8) |

测试框架: **cmocka**（`CMake/FindCMocka.cmake`；`XTRKCAD_TESTING` 默认 `ON`，但仅当 `CMOCKA_FOUND` 时才定义该选项）。制品仓有 `cmocka/2.0.2`。

## 编译步骤

配方化路径（`conanfile.py` 所走路径，CI 同款）：
```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

本地探索路径（定位平台问题用）：
```bash
# 1) 依赖（仓库 CI profile 带 os.version=6.0）
conan install . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing -of build
# 2) 配置 + 构建（Ninja 后端）
cmake -S <src> -B <build> -G Ninja -DCMAKE_TOOLCHAIN_FILE=<deps>/build/conan_toolchain.cmake
cmake --build <build>                     # 128 个目标，全绿
# 3) 上游测试
cd <build> && ctest --output-on-failure
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 依赖清点 | `Xtrakcad` 需 GTK+-2.0（`pkg_check_modules` REQUIRE）| 制品仓 `gtk2/2.24.33` 已就绪 |
| 2 | 文档目标 | `docs/` 依赖 pandoc（Debian 侧还列了 inkscape） | 默认构建不触发文档转换：`cmake --build` 128 目标全绿，配方未声明 pandoc 依赖 |
| 3 | `Libzip::Libzip` 目标缺失导致 configure 失败 | OHOS 不是 CMake 已知系统名 → `UNIX` 变量为假 → 顶层与子目录的 `if(UNIX)` 分支全部走错（如 `app/bin/CMakeLists.txt` 走到需要 `Libzip::Libzip` 的 else 分支） | 落源码补丁：`CMAKE_SYSTEM_NAME` 为 `HarmonyOS`/`OHOS` 时 `set(UNIX 1)`，让工程按 Unix 类平台处理；**不伪装 `CMAKE_SYSTEM_NAME`**（否则会载入错误的平台模块，见知识条目 E092） |
| 4 | 无 inkscape，位图目标无法生成 | 上游用 Inkscape 把 `app/bin/bitmaps/*.svg` 转 PNG 再转成 `.image1/.image3` C 头；制品仓无 inkscape（imagemagick 无 SVG 读委托且包内无 rsvg-convert，已实测排除） | 用制品仓 `librsvg/2.62.3.1.1`（静态库 + `librsvg-2.0.pc`）自建 `svg2png` 小工具，接受上游交给 Inkscape 的同一命令行形态（`INPUT.svg -h HEIGHT -o OUTPUT.png`），由 `CMake/FindInkscape.cmake` 找到 |
| 5 | conan 依赖目标名大小写不匹配 | CMakeDeps 生成小写 `libzip::libzip` / `cmocka::cmocka`，而工程 `CMake/FindLibzip.cmake`、`FindCMocka.cmake` 定义大写变量/目标 | 顶层 `CMakeLists.txt` 桥接两种写法（小写目标存在时映射到大写变量） |
| 6 | `gtk/gtkunixprint.h` 找不到（`app/wlib/gtklib/print.c:41`） | `CMake/FindGTKUnixPrint.cmake` 依赖 `.pc` 缓存前缀，conan 生成器目录里没有对应的 wrapper `.pc` | 改为按头文件实际存在性判定，并复用 GTK 自身库（能力探针，不做平台名判断） |
| 7 | `duplicate symbol: main` | `app/bin/unittest/defaultstest.c` 自带 wPref* 桩，与 `xtrkcad-wlib` 中的定义冲突 | 该测试只链 `dynstring`；同时补齐缺失的 `wPrefSetString` 桩 |
| 8 | `make: jobserver mkfifo ... Operation not permitted` | 构建沙箱禁用 mkfifo，GNU make 的 jobserver 无法工作 | 用 Ninja 后端 + `cmake --build` |
| 9 | `refresh-patch` 生成的 bitmaps 补丁 dry-run 失败 | `app/bin/bitmaps/CMakeLists.txt` 是**CRLF** 上游文件，而补丁工具按文本模式读源码（剥掉 CR）→ 生成的 LF 补丁无法套用到 CRLF 文件（`Hunk 1 FAILED 90/90`） | 该文件的适配版本改由 `ohos/bitmaps/` 承载、经 `exports_sources` 随配方交付，`build()` 中在打补丁后覆盖（见 `conanfile.py` 头注释）；其余 6 个补丁均为 LF 文件，走常规 `patches/` 通道 |

## 依赖版本

| 依赖 | 版本 | 制品仓 | 用途 |
|------|------|--------|------|
| gtk2 | 2.24.33 | ✅ | GUI 后端（UNIX 默认 `XTRKCAD_USE_GTK=ON`） |
| libzip | 1.11.4 | ✅ | `find_package(Libzip)` |
| zlib | 1.3.1 | ✅ | `find_package(Zlib)` |
| cmocka | 2.0.2 | ✅ | 单元测试框架（`XTRKCAD_TESTING`） |
| freeimage | 3.18.0 | ✅ | 上游仅 `WIN32` 必需（位图处理），OHOS 走内建路径 |
| pandoc | 3.10.1 | ✅ | 文档转换 |
| intltool / gettext | 0.51.0 | ✅ | i18n（`XTRKCAD_USE_GETTEXT`） |

## 验证结果

### 本地构建（R51 步骤2 前置）

```bash
cmake 配置 rc=0        # 不带任何平台伪装标志（无 -DUNIX=1 / -DCMAKE_SYSTEM_NAME=...）
cmake --build          # prog=[128/128]，failed=0
```

### 上游测试实测（R51 步骤2）

```bash
$ cd /storage/Users/currentUser/tmp/xtrkcad-build && ctest --output-on-failure
1/5 Test #1: DXFOutputTest ....................   Passed    0.09 sec
2/5 Test #2: PathsTest ........................   Passed    0.19 sec
3/5 Test #3: DefaultsTest .....................   Passed    0.12 sec
4/5 Test #4: ShortenTest ......................   Passed    0.12 sec
5/5 Test #5: DynStringTest ....................   Passed    0.10 sec
100% tests passed, 0 tests failed out of 5
Total Test time (real) =   0.65 sec
```

- **通过率 5/5（100%）**，24 个可运行 cmocka case 全部通过（上游活跃 26 个，含 2 个 MSW 专用不参与构建）。
- 上游共 6 个 ctest 注册项，第 6 个 `UTF8ConversionTest` 位于 `app/wlib/mswlib/`（MSW 专用路径），在 OHOS/Linux 侧不参与构建，故本平台可执行测试为 5 个——非裁剪、非跳过。
- 配方 `conanfile.py::build()` 内已接入 `cmake.test()`，CI 构建时自动执行同一组测试（`build_requirements()` 内 `test_requires("cmocka/2.0.2")`），无本地环境依赖。

## 上游测试用例修改说明

只动了让上游测试**能在 OpenHarmony/Linux 上编出并可链接**的最小内容，**未修改任何断言、参数或期望值**（测试逻辑与上游逐字一致）：

| 文件 | 改动 | 原因 |
|------|------|------|
| `app/bin/unittest/CMakeLists.txt` | 为单测目标补 include 搜索路径 | `defaultstest.c` / `pathstest.c` 引用 `common.h`、`dxfformat.h`，上游在 MSW 工程文件里带上了这些路径，CMake 规则未带 |
| `app/bin/unittest/CMakeLists.txt` | `defaultstest` 只链 `dynstring`（原链 `xtrkcad-wlib`） | 该测试自带 `wPref*` 桩，与 `xtrkcad-wlib` 中的定义冲突 → `duplicate symbol: main` |
| `app/bin/unittest/defaultstest.c` | 补一个缺失的 `wPrefSetString` 桩 | 该测试自带其余 wPref* 桩，缺 `wPrefSetString` 导致链接未定义符号 |

补全说明：未**新增**上游测试用例；新增的 `test_package/`（消费者视角用例）属于本仓库 L1 包测试，不计入上游用例数。

## 注意事项

- 工程规模大（246 个 `.c`，含 GTK GUI + 帮助文档），已按 W3/CI 同源配置登记超时预算：`ci/config/build_timeouts.txt` 中 `xtrkcad/5.3.1ga`。
- `docs/` 子目录的 pandoc/inkscape 依赖未阻塞默认构建（`cmake --build` 128 目标全绿，未触发 pandoc）。
- GUI 运行时需要 X 服务器，鸿蒙 PC 无 X：适配验证在编译/链接层 + 上游 ctest + 消费者用例（链接包内 `libdynstring.a` 并实跑）+ `svg2png` 实跑产出合法 PNG。
---

**编译结束**: 2026-10-01 22:22
**最终状态**: built
