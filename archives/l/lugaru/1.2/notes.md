# lugaru 1.2 适配笔记

## 编译环境

- 构建系统: cmake（上游 `CMakeLists.txt`，340 行；无 autotools/meson 入口）
- 编译日期: 2026-10-18
- 编译器: clang / clang++（ohos-sdk 26.0.0.18，`-stdlib=libc++`）
- 目标: OHOS / aarch64 / armv8 / musl / libc++（profile `ci/conan/profiles/ohos-aarch64`，cppstd=17）
- Conan: 2.29.1
- 状态: built（本地 `conan create` 端到端通过；尚未走 release 流水线 `conan upload`，故按归档规范记 built）

## 软件辨识（先做，避免重复适配）

- **正主确认**：`git ls-remote --tags https://gitlab.com/osslugaru/lugaru.git` 实测
  `refs/tags/1.1` = 53bbd7b11ba7558692b00d936d3103750fcb430b、`refs/tags/1.2` =
  `c7b99378439735c60f84869b05c6ebde53083667`（**tag 无 v 前缀**）。
- GitHub `WolfireGames/lugaru` **没有 1.2 tag**：`…/archive/refs/tags/1.2.tar.gz` 直链
  实测 404（ghfast/gh-proxy/codeload 三处同结果）⇒ 不是本任务上游。
- 旁证：Debian `lugaru` 源码包的 `debian/watch` 指向 `gitlab.com/osslugaru/lugaru/tags`。
- **归档查重**：upstream/main 树内 `git ls-tree` 查 `archives/l/lugaru` = **0 文件**（非重复适配）。

## 直链与校验（复跑留读数）

```
URL    https://gitlab.com/osslugaru/lugaru/-/archive/1.2/lugaru-1.2.tar.gz
HTTP   200
BYTES  35789210
SHA256 6e2acc14d62f2bf6b329ddbed8d50d1428ae159b986be1d7833c004a7bfa5a9f
顶层目录 lugaru-1.2（get(strip_root=True) 命中）
```

（同 tag 的 `.tar.xz` 变体实测 403/5407 B，不作为源。）

## 编译步骤

```bash
export CONAN_HOME=$HOME/tmp/ch/home-zhuli7-lugaru
export OHC_PROJECT_DIR=<worktree>
python3 scripts/ohc-run.py init-build lugaru 1.2 \
    --url=https://gitlab.com/osslugaru/lugaru/-/archive/1.2/lugaru-1.2.tar.gz
python3 scripts/ohc-run.py build lugaru 1.2          # 生成骨架（本包随后手工改写为 CMake 配方）
python3 scripts/ohc-run.py conan-verify lugaru 1.2   # G0-G4 + L2/L4/L5
```

本地与 CI 同源的验证命令：

```bash
conan create archives/l/lugaru/1.2 \
    -pr:h=./ci/conan/profiles/ohos-aarch64 -pr:b=./ci/conan/profiles/ohos-aarch64 \
    --build=lugaru/*
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `CMake Error at CMakeLists.txt:3 (cmake_minimum_required): Compatibility with CMake < 3.5 has been removed` | 平台 CMake 4.1.2 拒绝 `cmake_minimum_required(VERSION 3.0)` | patch 0001 抬到 3.5 |
| 2 | `CMake Error at CMakeLists.txt:4 (cmake_policy): Policy CMP0004 may not be set to OLD`（第 1 条修完后的下一个首错） | CMake 4 已删除 CMP0004 的 OLD 行为 | patch 0001 删掉该 `cmake_policy(SET CMP0004 OLD)` 行 |
| 3 | `XYZ.hpp:58:24: error: ISO C++17 does not allow 'register' storage class specifier`（45 个 .cpp 里 20 个同源失败） | profile 钉 `compiler.cppstd=17`，conan 的 `CMAKE_CXX_STANDARD=17` 由 **CMake 追加在 `CMAKE_CXX_FLAGS` 之后**，上游写的 `--std=gnu++11` 无论怎么拼接都无法胜出（实测编译行结尾为 `… --std=gnu++11 -O3 -DNDEBUG -std=c++17`）；`Source/Math/XYZ.hpp` 两处 `fast_sqrt(register float)` 在 C++17 下 clang 直接报错 | patch 0001 去掉两处 `register`（自 C++11 起就是无意义提示符） |
| 4 | `undefined reference to 'gluPerspective'`（configure 期 `-- Found OpenGL: …/gl4es…/libGL.so` 一切正常，链接期才炸） | gl4es 的包**装了 `include/GL/glu.h` 头但不实现 GLU**：`llvm-nm -D libGL.so.1` 的 45 条 `glu*` 命中全是 `glUniform*`，`gluPerspective` 一条没有；且 CMake 自带 `FindOpenGL` 只在显式请求 `GLU` 组件时才去找 `OPENGL_glu_LIBRARY`，上游只写 `${OPENGL_LIBRARIES}` ⇒ 即使有 libGLU 也不会入链接行 | `requires("glu/9.0.3")`（实测导出 `T gluPerspective`/`T gluLookAt`）+ 播种 `-DOPENGL_glu_LIBRARY` + patch 0001 把它追加进 `LUGARU_LIBS` |
| 5 | `Could NOT find OpenAL/PNG/JPEG/ZLIB/OggVorbis` 或变量为空 | 上游消费 Find 模块的**遗留变量**（`${OPENAL_LIBRARY}`/`${PNG_LIBRARY}`/`${JPEG_LIBRARY}`/`${ZLIB_LIBRARIES}`/`${SDL2_LIBRARIES}`/`${OPENGL_LIBRARIES}`/`${OGG_LIBRARY}`/`${VORBIS*_LIBRARY}`），而 CMakeDeps 只产出现代 IMPORTED target | configure 前逐个 `-D` 播种库与头目录（含 `PNG_PNG_INCLUDE_DIR`、`VORBIS_INCLUDE_DIR`/`OGG_INCLUDE_DIR`） |
| 6 | `pkg_check_modules(SDL2 sdl2 REQUIRED)` 找不到 sdl2 | 上游对 SDL2 走 pkg-config，而依赖的 `.pc` 由生成器产出、不在默认搜索路径 | `PkgConfigDeps` + 在 configure 命令前置 `PKG_CONFIG_PATH=<generators>`；`tool_requires("pkgconf/3.0.6")` 保证 CI worker 也有 pkg-config |
| 7 | `png.h not found` 风险 | libpng 的头在 `include/libpng16/png.h`、SDL2 的头在 `include/SDL2/SDL.h`，只加依赖的 `include/` 根不够 | `_header_dir()` 递归定位头文件所在目录，随 `tc.extra_cflags/extra_cxxflags` 一起 `-I` |
| 8 | 显式 `requires("mesa/24.3.4.1.1.1")` 解不出：`Missing prebuilt package for 'libxrender/0.9.12'` | 该 mesa 版本的闭包含整套 X11（libx11/libxcb/xorgproto/xtrans→libxrender），ohpcd 没有该配置的二进制 | 不手工钉 mesa：`glu/9.0.3` 的 `cpp_info.requires=["mesa::mesa"]` 会带进 `mesa/24.3.4.1`（有二进制），GL 实现面由它兜底 |
| 9 | 消费者测试两条 `DT_NEEDED` 断言 FAIL，但 `readelf -d` 明明有 libGL.so.1/libGLU.so.1 | 测试自带的手写 ELF 解析器把"第一个 SHT_STRTAB"当 `.dynstr` 用，读出来的是 `.dynsym` 符号名而不是 `.dynamic` 里的 DT_NEEDED | 改为解析 `SHT_DYNAMIC`（`d_tag==1` → `.dynstr` 下标），串表按 `.dynamic` 的 `sh_link` 取；修后 `PARSED_NEEDED` 与 `readelf -d` 逐字一致 |

> 第 9 条是**测试自身的缺陷**（不是产物问题）：作为过程数据如实留档，修法也写在这里，避免下一个包重复踩。

| 10 | W3 本地 CI：`[fail] L0c: No test source files in test_package/`（`no_test_sources`） | L0c 要求 `test_package/` 下有 `.c/.cpp/.cc/.cxx/.sh/.py` 测试源文件（**排除** `conanfile.py` 本身）；本包最初的 CLI 包装脚本是运行时写进临时目录的，包内只有 `conanfile.py` + `MANIFEST.yml` | 把 CLI 冒烟驱动改成随包提交的 `test_package/test_lugaru.sh`（真实测试资产，也更可读），`conanfile.py` 改为调用它 |
| 11 | W3 本地 CI：`[fail] L0g: conanfile.py 禁止硬编码 remote 名称 (-r=)`（`hardcoded_remote`） | L0g 用 `grep` 扫 `conan (install|download|create|upload|export)…-r[= ]` 字面量（**不排除 docstring**，与 L0i 的 AST 解析不同）；本包 docstring 里写了一句 `conan download --only-recipe opengl/4.6 -r=ohpcd` 的实测证据 | 把该处改成不带 `-r=` 的表述（只是注释文字，行为零改动）；W0 原始命令仍保留在本笔记与 manifest 里 |

## 源码修改

`patches/0001-cmake-ohos-compat.patch`（4 处，逐条都有必要性）：

1. `cmake_minimum_required(VERSION 3.0)` → `3.5`（CMake 4.x 硬要求）
2. 删除 `cmake_policy(SET CMP0004 OLD)`（CMake 4.x 已移除 OLD 行为）
3. `set(LUGARU_LIBS …)` 追加 `${OPENGL_glu_LIBRARY}`（把 libGLU 真正接进链接行）
4. `Source/Math/XYZ.hpp` 两处 `fast_sqrt(register float …)` 去掉 `register`（C++17 非法）

**未做的两件事（明确边界）**：① 没有把 `find_package(OpenGL REQUIRED)` 改成 GLESv2+EGL——
本包是纯固定管线渲染器（`glBegin/glEnd/glMatrixMode/glVertex3f/glOrtho/glColor4f`…），
GLES2 没有这些入口，直连 GLESv2 只会从"缺 GLU"变成"缺 200+ 固定管线符号"；
② 没有改上游渲染代码，适配全部以"配方 + 4 行构建期补丁"形态落地。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| zlib | 1.3.1.1 | 直接依赖（`${ZLIB_LIBRARIES}`） |
| libpng | 1.6.58 | 直接依赖（`find_package(PNG)`，头在 include/libpng16） |
| libjpeg-turbo | 3.2.0 | 直接依赖（`find_package(JPEG)`，`libjpeg.so.62`） |
| libogg | 1.3.6 | 直接依赖（上游 `FindOggVorbis.cmake` 要 `ogg/ogg.h`） |
| libvorbis | 1.3.7 | 直接依赖（vorbis/vorbisfile/vorbisenc 三个库变量都要） |
| openal | 1.25.2 | 直接依赖（音频；包内为静态 `libopenal.a`） |
| sdl2 | 2.30.10 | 直接依赖（窗口/输入；包内为静态 `libSDL2.a`） |
| gl4es | 1.1.6 | OHOS GL 栈：`libGL.so.1`（GL 1.x over GLES），**不含 GLU 实现** |
| glu | 9.0.3 | GLU 实现：`libGLU.so.1`（导出 `gluPerspective`/`gluLookAt`） |
| mesa | 24.3.4.1 | **传递依赖**（`glu` 的 `cpp_info.requires`），OpenGL 实现面 |
| pkgconf | 3.0.6 | `tool_requires`（`pkg_check_modules` 用） |

**W0 实测**：上面 9 个直接/工具依赖逐个 `conan download --only-recipe` 与一次
`conan install --build=never` 全绿；`opengl/4.6` 不在 ohpcd 远端
（`conan download --only-recipe opengl/4.6 -r=ohpcd` rc=1）。

## 验证结果

```bash
$ conan-verify lugaru 1.2   # = conan create + G0-G4 + L2/L4/L5
✅ G0 预构建风险评估 PASS   ✅ G1 配方完整性 PASS   ✅ G2 conan create PASS
✅ G3 系统同名库隔离 PASS   ✅ G4 产物完整性 PASS
ℹ️ L2/L4/L5: 跳过（报告记 "无 cache 路径"——本包为纯 application 包、无 lib/，
   门禁侧未取到 cache 路径；功能面由 test_package 的真实执行覆盖，见下）

$ conan create archives/l/lugaru/1.2 -pr:h=… -pr:b=… --build=lugaru/*
lugaru/1.2@ohpcd/stable (test package): [test] lugaru/1.2 消费者校验：6 用例、24 项断言，通过 24、失败 0
lugaru/1.2@ohpcd/stable (test package): HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true,
  "discovered": 6, "passedCount": 6, "assertions": 24, "assertionsPassed": 24}
```

运行时（真实执行被测二进制，无 GPU/合成器）：

```text
--------------------------------------------------------------------------
Lugaru HD: The Rabbit's Foot, by Wolfire Games and the OSS Lugaru project.
...
Version 1.2 -- Release build
--------------------------------------------------------------------------
LIBGL: Shutting down
```

三条 CLI 断言实测：`--version` rc=0 且 stdout 含 `Version 1.2`；
`--help` rc=0 且 usage 含 `-v, --version`/`-h, --help`；
未知开关 rc=1 且输出含 `Unknown option`（`main.cpp` 的选项解析分支，全部在 SDL 初始化之前返回）。
`bin/lugaru` 的 `DT_NEEDED` 实测（readelf 与测试解析器一致）：
`libpng16.so.16, libjpeg.so.62, libGL.so.1, libGLU.so.1, …/libvorbisfile.so, libogg.so, libc++_shared.so, libc.so`。

### 五维测试账本（正文/notes/报告同源）

| 维度 | 数值 | 说明 |
|------|------|------|
| `N_static` | 0 | 上游无自动化测试：顶层 `CMakeLists.txt`/`CMake/Modules/` 无 `enable_testing()`/`add_test()`/`ctest`；全仓 `find -iname "*test*"` = 0；`.gitlab-ci.yml` 只有 `build_gcc`/`build_clang` 两个构建 stage |
| `N_registered` | 0 | 无 CTest 目标可注册 |
| `N_executed` | 0 | 无上游用例可执行（分母为 0，非"少跑"） |
| 未执行分类数 | 0 | 无被跳过的上游用例；真实渲染/输入/音频属**不可覆盖面**，已在 `test_package/MANIFEST.yml` 逐条申报 |
| `N_consumer` | 6 用例 / 24 项断言 | `test_package`：静态 3 例（16 断言）+ 真实执行 3 例（8 断言），全部通过 |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/lugaru` | 3947200 B | 游戏主程序（ELF64 LSB AArch64、ET_DYN/PIE、`PT_INTERP=/lib/ld-musl-aarch64.so.1`） |
| `bin/Data/` | 39 MB / 542 文件 | 游戏资源（Animations/Campaigns/Dialogues/Maps/Models/Skeleton/Sounds/Textures），与可执行文件同目录（运行期 `DATA_DIR="Data"`） |
| `share/man/man6/lugaru.6` | — | 用户手册 |
| `licenses/` | — | `COPYING.txt`（GPL-2.0）、`CONTENT-LICENSE.txt`（CC-BY-SA）、`AUTHORS` |

## 注意事项

- **未覆盖面**：进入主循环需要 GL 上下文与显示设备，本机无 Wayland 合成器/GPU 会话，
  因此渲染、输入、音频与关卡流程未在 CI 中执行；三条 CLI 用例只覆盖"启动前的选项解析与横幅"。
- **产物形态披露**：`DT_NEEDED` 中 `libvorbisfile.so` 被记成**绝对路径**（conan 侧该库未带
  SONAME），同机解析正常，跨机分发不可移植（与 E2118 的 bare SONAME 同族）；其余条目均为正常 SONAME。
- **测试自身的两处修正**（过程数据）：CLI 包装脚本参数顺序写错（少传 log 参数）、
  手写 ELF 解析器取错字符串表；两者都已修正并复跑，最终 24/24。前几轮 G2 红均为
  "修一条、看下一条首错"的正常迭代，不是同一错误重复。
- **不需要 `-DVERSION`**：上游版本常量硬编码在 `CMakeLists.txt`（1.2.0），
  `Version.hpp` 由 `configure_file` 生成，实测横幅打印 `Version 1.2 -- Release build`。
---

**编译结束**: 2026-10-18 07:30
**最终状态**: built
