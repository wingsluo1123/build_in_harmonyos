# uqm 0.8.0 适配笔记

The Ur-Quan Masters（星际控制 II 开源复刻版）0.8.0 · HarmonyOS PC (aarch64-unknown-linux-ohos)

## 编译环境

- 构建系统: custom（上游自研 `build/unix/build.sh`，非 autotools/cmake/meson）
- 编译日期: 2026-10-16
- 编译器: clang 15.0.4（OHOS SDK `aarch64-unknown-linux-ohos`）
- 状态: built（conan-verify G0-G4 + L2/L4/L5 全通过；CI upload 在合并 main 后由发布流水线执行）
- 源码: `uqm-0.8.0-src.tgz`（SourceForge 项目 sc2 官方发布）
  sha256 `24f2f7db9cf7faf53b95f9e2580e6f596205a98ed0c335cfe834c64785ad4f5a`

## 编译步骤

上游 `./build.sh uqm config` 是**交互式文本菜单**（无命令行参数），上游 INSTALL
明确说明无人值守场景应「consult the config.state file ... builds will then skip
the configure step」。因此配方在 `build()` 内合成 `config.state`
（格式与 `build/unix/menu_functions` 的 `menu_save_*` 输出一致：
`CHOICE_<name>_VALUE='...'` / `INPUT_<name>_VALUE='...'`），再走
`reprocess_config` 目标生成 `build.vars` / `config_unix.h` / `uqm-wrapper`，
全程不进入菜单：

```bash
# 1. 生成 config.state 后：非交互配置（跳过菜单，生成 build.vars 等）
./build.sh uqm reprocess_config

# 2. 编译（R9：单作业，确定性）
./build.sh uqm -j1

# 3. 安装到 package_folder（bin/ + lib/ + share/）
./build.sh uqm install
```

配置选项（config.state 实测值）：

| 菜单项 | 取值 | 说明 |
|--------|------|------|
| debug | nodebug | -O3 -DNDEBUG |
| graphics | sdl2 | SDL2 渲染后端（`sdl2-config` 探测） |
| sound | mixsdl | 内置 MixSDL 混音（实测走 OHOS ohaudio） |
| mikmod | internal | 内置 libmikmod，**不依赖外部 libmikmod** |
| ovcodec | standard | Xiph libogg + libvorbis（pkg-config 探测） |
| netplay | full | IPv4+IPv6 超级机甲对战 |
| joystick | enabled | SDL 手柄 |
| ioformat | stdio_zip | 直读 + .zip（zlib） |
| accel | asm | 平台加速 |
| threadlib | sdl | SDL 线程 |

外部依赖的接入方式（UQM 三种探测机制各不相同）：

- `sdl2-config`（SDL2 专用脚本）→ 由 sdl2 包的 `bindirs` 提供，配方把它前置到 PATH
- `pkg-config`（vorbisfile / zlib / libpng 探测）→ 配方 `generators = "PkgConfigDeps"`
  生成 .pc，`PKG_CONFIG_PATH` 指向 generators 目录
- libpng 库探测直接写死 `-lpng` 且不带 `-L` → 配方把各依赖
  `includedirs/libdirs` 注入 `CFLAGS/LDFLAGS`（UQM 的 CFLAGS/LDFLAGS 从环境继承，
  上游 `config_proginfo_host` 注释中已说明这一用法）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 阶段报 `can't create /tmp/build.$$.tmp: Read-only file system`，libpng 探测失败后 exit 1 | `build/unix/config_functions:19` 硬编码 `TEMPFILE="/tmp/build.$$.tmp"`；OHOS `/tmp` 只读（E002） | 补丁 0001 改为 `${TMPDIR:-/tmp}/build.$$.tmp`（按 SKILL §7 用 `$TMPDIR`），配方另把 TMPDIR 指到 `build_folder/tmp` |
| 2 | `netmanager_bsd.c` 编译失败：`unknown type name 'fd_set'`、`FD_SETSIZE`/`select` 未声明（18 个 error） | musl 的 `<sys/types.h>` 不再顺带引入 `<sys/select.h>`，而该文件未显式包含；glibc 下恰好能过 | 补丁 0002 在系统头区块加 `#include <sys/select.h>` |
| 3 | 上游构建系统把编译器写死为 `gcc`（`config_proginfo_build: PROG_gcc_FILE="gcc"`），本机/CI 无 gcc | 上游只考虑 gcc，交叉编译支持靠 `BUILD_HOST` 环境变量而非 CC | 配方在 `build_folder/toolchain-shim/gcc` 生成 shim（`exec <conan clang> "$@"`，R49 私有目录），前置到 PATH |
| 4 | `./build.sh uqm config` 会阻塞在交互菜单，CI 无法自动执行 | 上游 configure 是文本菜单，无 CLI 参数 | 合成 `config.state` + `reprocess_config`（上游 INSTALL 认可的方式），见上 |
| 5 | 安装后 `lib/uqm/uqm` 直接运行报 `Error loading shared library libpng16.so.16 / libvorbisfile.so / libogg.so` | libpng/libogg/libvorbis 为共享依赖，位于 Conan 缓存 | 配方在每个依赖的 libdir 注入 `-Wl,-rpath`；test_package 另用 VirtualRunEnv（conanrun） |
| 6 | 直接运行 `uqm` 报 `*** FATAL ERROR: Could not load basic content ***` | 游戏**内容包**（`uqm-0.8.0-content.uqm`）是上游单独发布的资源，不在源码包内 | 非适配缺陷；test_package 以此作为「SDL 初始化 + 音频 + content 挂载全部成功」的可观测证据（见验证结果） |

> 说明（工具盲点）：`ohc-run.py refresh-patch --auto` 的规则模式把路径中含
> `build` 目录的改动排除（`refresh_patch.EXCLUDE_DIRS`），而 UQM 的构建脚本全部
> 位于 `build/unix/`，导致补丁 0001 被漏掉。本次改用 `track-edit` 编辑追踪器的
> 精准模式（`无需排除规则`）生成补丁，规避该盲点；已在 SKILL_FEEDBACK 中上报。

## 源码修改

| 补丁 | 文件 | 修改 |
|------|------|------|
| `0001-build-unix-config_functions.patch` | `build/unix/config_functions` | `TEMPFILE="/tmp/..."` → `TEMPFILE="${TMPDIR:-/tmp}/..."`（1 行，OHOS 只读 /tmp） |
| `0002-src-libs-network-netmanager-netmanager_bsd.c.patch` | `src/libs/network/netmanager/netmanager_bsd.c` | 新增 `#include <sys/select.h>`（1 行，musl 头文件可见性） |

两个补丁均为可移植性改动，**不含 `__OHOS__` 等平台宏**，也不改变上游行为
（glibc/BSD/macOS 上 `<sys/select.h>` 存在且语义相同；`${TMPDIR:-/tmp}` 在未设置
TMPDIR 时回退原路径）。

## 依赖版本

全部为制品仓 ohpcd 已发布配方（R36 前置检查通过）：

| 依赖 | 版本 | 说明 |
|------|------|------|
| sdl2 | 2.32.10 | 静态（libSDL2.a），链接 `-lohaudio -lnative_window -lEGL -lGLESv2` |
| libpng | 1.6.58.3 | 共享 |
| libvorbis | 1.3.7 | 共享（传递引入 libogg/1.3.6） |
| zlib | 1.3.2 | libpng 传递依赖，UQM 直接 `-lz` 链接 .zip 读取 |

上游可选依赖 **libmikmod 未使用**（`mikmod=internal`，Tracker 音乐由源码内
`src/libs/mikmod` 提供），故不构成 R36 依赖缺口。

## 验证结果

```bash
# conan create（干净源码 + 补丁）
conan create archives/u/uqm/0.8.0 -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 --build=uqm/*
# → Build succeeded + test_package 4/4 PASS

# conan-verify（G0-G4 + L2/L4/L5）
python3 scripts/ohc-run.py conan-verify uqm 0.8.0
# → ✅ 配方验证通过: uqm 0.8.0（配方可发布；本归档标 built，upload 由合并后的发布流水线执行）

# test_package 消费者验证（4 项断言）
check1 --version -> 0.8.0                                    # 版本号
check2 --help 含 Ur-Quan Masters 横幅 与 --contentdir 选项     # 选项表
check3 --contentdir=/nonexistent-uqm-content -> "Could not find content" + 非 0 退出
check4 启动器默认挂载随包 content 且 SDL2/OHOS 音频栈真实初始化：断言日志同时包含
       "Using '<pkg>/share/uqm/content' as base content dir."、
       "Using SDL version"、"SDL audio subsystem initialized"、"using ohaudio"
       （进程最终止于上游内容包缺失提示
        "*** FATAL ERROR: Could not load basic content ***"，属预期终态）
# test uqm 0.8.0: 4/4 checks PASS
```

`check4` 的实际日志（证明平台栈真实工作）：

```
Using SDL version 2.32.10 (compiled with 2.32.10)
Using '<pkg>/share/uqm/content' as base content dir.
SDL initialized.
SDL2 renderer 'software' selected.
SDL audio subsystem initialized.
    using ohaudio at 44100 Hz 16 bit stereo, 4096 samples audio buffer
Mixer initialized.
*** FATAL ERROR: Could not load basic content ***   ← 缺上游单独分发的内容包
```

- 编译状态: built（编译通过；clang 15，aarch64-unknown-linux-ohos）
- 上游测试: 上游 0.8.0 未提供任何测试用例（无 tests/、无 check/ctest/meson 目标，
  证据见 `test_package/MANIFEST.yml`），上游用例通过率 N/A
- 新增测试: test_package 4 项消费者断言，4/4 通过

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/uqm` | 上游启动器（wrapper，自动补 `--contentdir`） |
| `lib/uqm/uqm` | 游戏主程序（ELF aarch64，带依赖 rpath） |
| `share/uqm/content` | 随源码包提供的 content 索引 |

## 注意事项

1. **内容包不随本包安装**：`uqm-0.8.0-content.uqm`（及可选的 voice / 3domusic）是
   上游 SourceForge 单独发布的游戏资源，不属于源码包；用户需自行下载并放入
   `share/uqm/content/packages/`（或通过 `--contentdir` 指定）后才能真正开局。
   本适配交付的是可运行的**程序本体**。
2. `lib/uqm/uqm` 已注入依赖 rpath 指向 Conan 缓存的 libpng/libogg/libvorbis；
   下游通过 conan 消费本包时依赖链由 Conan 解析（`conan install` 会拉齐）。
3. `--configdir` 建议显式指定到可写目录。

## 对话记录

### 2026-10-16 uqm 0.8.0 适配全过程

**流程**: init-build（SourceForge 官方 tarball，sha256 核验）
→ 源码解压（修正 init-build 嵌套源码误判：tarball 顶层即 uqm-0.8.0/）
→ 手工探索编译（config.state + reprocess_config → build.sh uqm -j1 → install）
→ refresh-patch（track-edit 精准模式）→ conan-init/手写配方 → conan-verify G0-G4 + L2/L4/L5
→ finish（W2 结构 + R36 依赖 + W3 本地 CI）→ W4 审计 → PR。

**关键修复与判定**:

- [E754] 自研 configure 硬编码 `/tmp/build.$$.tmp`（OHOS /tmp 只读）→ 补丁改为
  `${TMPDIR:-/tmp}` + 配方注入 TMPDIR → ✅ 已修复
- [E757] musl 下 `fd_set`/`FD_SETSIZE`/`select` 需显式 `<sys/select.h>` →
  补丁新增 1 行 include → ✅ 已修复
- 上游写死 `gcc` → 配方生成私有 gcc shim 转发 Conan clang（R49 私有目录）→ ✅ 已解决
- 交互式菜单 configure → 合成 `config.state` + `reprocess_config`（上游 INSTALL 认可）→ ✅ 已解决
- 共享依赖找不到 → 注入依赖 libdir rpath + test_package VirtualRunEnv → ✅ 已解决
- 内容包（uqm-0.8.0-content.uqm）不在源码包内 → 非适配缺陷，已在「注意事项」写明

**判定依据**: conan-verify G2 `conan create` 干净构建通过；W3 本地 CI 模拟
（setup.sh + build_and_test.sh）JC/KC/L0 全通过、test_package 4/4 断言通过。
---

**编译结束**: 2026-10-16 19:53
**最终状态**: built
