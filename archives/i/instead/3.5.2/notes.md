# instead 3.5.2 适配笔记

## 编译环境
- 构建系统: **cmake**（src/ 下另有 legacy Makefile/Rules.make.*，仅 Unix 守护，本适配走 CMake）
- 编译日期: 2026-07-22
- 编译器: clang 15 / clang++
- 状态: in_progress
- 上游: https://github.com/instead-hub/instead
- License: MIT

## 路径决策：**路径 A**（核心解释器 + SDL2 链 + Lua，关闭音频/GTK/iconv 可选项）

### 实际依赖（已核实）

| Conan 依赖 | 用途 | 必修？ |
|---|---|---|
| `lua/5.4.x` | 嵌入式 Lua（`WITH_LUAJIT=OFF`，因 OHOS 无 LLVM jit） | 必需 |
| `sdl/2.30.x` | 渲染主框架 `FIND_PACKAGE(SDL2 REQUIRED)` | 必需 |
| `sdl_image/2.x` | `FIND_PACKAGE(SDL2_image REQUIRED)`（BMP/PNG/JPG） | 必需 |
| `sdl_ttf/2.x` | `FIND_PACKAGE(SDL2_ttf REQUIRED)`（TTF 字体） | 必需 |
| `sdl_mixer/2.x` | `FIND_PACKAGE(SDL2_mixer REQUIRED)`（音频；sound.c 深度耦合） | 必需 |
| `zlib/1.3.x` | `FIND_PACKAGE(ZLIB REQUIRED)` | 必需 |
| **NOT libzip** | INSTEAD 使用 **bundled minizip**（src/unzip.c + iowin32.c） | 无需 |

### 关闭的可选子系统

- `WITH_LUAJIT=OFF`（OHOS 无 LLVM/LLVM-JIT，强制 vanilla Lua）
- `WITH_ICONV=OFF`（OHOS bionic iconv 不支持全部 CP12xx；INSTEAD 默认 UTF-8，可关）
- `WITH_GTK2=OFF` / `WITH_GTK3=OFF`（无 GTK）
- `WITH_HARFBUZZ=OFF`（无 HarfBuzz）
- `SYSTEMWIDE=OFF`、`STANDALONE=OFF`（不 install 进系统，conan stage 即可）

## 已识别的源码风险点（探索阶段）

| 文件 | 行 | 问题 | 解决策略 |
|---|---|---|---|
| `src/CMakeLists.txt` | 111-115 | `FIND_PACKAGE(LuaJIT REQUIRED)` 默认 ON → conan 无 luajit 时硬失败 | 显式 `-DWITH_LUAJIT=OFF`；无源码 patch 需要 |
| `src/CMakeLists.txt` | 14-18 | `OPTION(WITH_GTK3 ON)` / `OPTION(WITH_ICONV ON)` 默认开启 | conanfile.py 显式传 `-DWITH_GTK2=OFF -DWITH_GTK3=OFF -DWITH_ICONV=OFF` |
| `src/instead/snprintf.c` | 178-193 | `__linux__` 分支调 `setlocale(LC_ALL, "")` 在 OHOS 返回 NULL | patch: 加 `__OHOS__` 守护，强退 `"C"` |
| `src/instead/instead.c` | 1136-1143 | 同上 | 同上守护 |
| `src/iowin32.c` | — | iowin32.c 是 Windows-only zip32 API stub；cmake 未守护非 Windows 构建 | patch: 加 `#ifdef _WIN32` 守护（当前在 Unix 上链接会引入 __imp_ 同名符号） |
| `src/instead/instead.h` | — | `extern lua_State*` 嵌入 → 链接时需 link Lua | `cpp_info.libs` 不暴露 lua（私有依赖） |

## 编译步骤（预期）

```bash
cd $BUILD_SRC_DIR
mkdir build && cd build
cmake \
  -DCMAKE_SYSTEM_NAME=OHOS \
  -DCMAKE_TOOLCHAIN_FILE=$OHOS_TOOLCHAIN \
  -DBUILD_SHARED_LIBS=OFF \
  -DWITH_LUAJIT=OFF \
  -DWITH_GTK2=OFF -DWITH_GTK3=OFF \
  -DWITH_ICONV=OFF \
  -DWITH_HARFBUZZ=OFF \
  -DSYSTEMWIDE=OFF -DSTANDALONE=OFF \
  -DCMAKE_BUILD_TYPE=Release \
  ..
make -j$(nproc)
```

## 验证策略

- **conan create** 成功后产物 = `sdl-instead` 可执行文件
- **test_package** 必须真调 API（`instead_init` / `instead_cmd` / `instead_done`）—但 cmake 没暴露 lib：
  - 决定：test_package 内部 **复编译 `src/instead/*.c` 子集**（instead.c、util.c、list.c、cache.c、idf.c、tinymt32.c、lfs.c），跳 SDL 渲染层，纯解释器 API 路径
  - 链接 lua/5.4 + zlib
  - 加载 `games/tutorial`（上游 .game fixture）作为输入

## 当前 W0 阶段 G2 已知阻塞

**R36 阻塞**：conan-verify G2 在 host Conan 解析 conancenter 上的 `sdl/2.30.9` 时被拒绝：

```
cmake/3.31.12: ERROR: Package 'fc3eeb021243959114a0318489539cad6d087e28' build failed
KeyError: 'OHOS'
```

**根因**：conancenter 上的 `sdl` / `lua` / `sdl_image` / `sdl_ttf` / `sdl_mixer` 配方目前不支持 `settings.os=OHOS`（它们的源码字典是按 Linux/Windows/Mac 枚举键索引），因此 cross-compile OHOS 时报 KeyError。`zlib` 同理。

**R36 正确路径**（拓扑序先行）：
1. 在 `archives/z/zlib/<ver>/` 先迁移 zlib（含 OHOS cross-compile 适配）  ✅ feat/zlib-1.3.1（本地）
2. 然后 `archives/l/lua/<ver>/` 迁移 lua  ✅ feat/lua-5.4.7（本地）
3. 然后 `archives/s/sdl/<ver>/`、`s/sdl_image/<ver>/`、`s/sdl_ttf/<ver>/`、`s/sdl_mixer/<ver>` — SDL2 链路未迁移；本轮迁移走的是 **SDL3 链路**：
   - feat/sdl3-3.4.8
   - feat/sdl3_image-3.4.4
   - feat/sdl3_ttf-3.2.2（额外依赖 freetype/2.14.3）
   - feat/sdl3_mixer-3.2.4
4. INSTEAD 本体需 SDL2→SDL3 的源码层适配（`src/sdl-instead.c` 等多处 API 改名）才能消费这批 SDL3 配方。该 PR 范围外。

**@ohpcd/stable 推送状态**：
- 已迁移的 6 个配方（lua/5.4.7、sdl3/3.4.8、sdl3_image/3.4.4、sdl3_ttf/3.2.2、sdl3_mixer/3.2.4、freetype/2.14.3）目前**只在本地 conan cache**，未推送到 ohpcd 远端制品仓（远端要求鉴权）。
- @ohpcd 远端目前只携带 zlib/1.3.1 一个 OHOS 适配配方。
- 故本仓库 `self.requires(...)` 的 deps 仍按 `conancenter` 解析；待 ohpcd 制品仓补齐后，可批量加 `@ohpcd/stable` 后缀让 conan 优先解析本地 OHOS-friendly 制品。

**G2 重跑结果（2026-07-22 22:53）**：
- 状态：FAIL（同 W0，原因未变）
- 失败位置：`cmake/3.31.12` 拉取时 `KeyError: 'OHOS'`
- 阻断层：transitive 依赖 cmake 自身的 conandata.yml 不识别 `settings.os=OHOS`
- 根因：conancenter 全链路配方（cmake、sdl、lua、zlib、sdl_*）默认按 `Linux/Windows/Mac` 枚举键索引源码，跨编译 OHOS 即报 KeyError
- 本 PR 不解决：阻塞点在 transitive 依赖侧的 os 枚举缺失，需要上游 PR 补 `OHOS` 分支，或在 ohpcd 制品仓批量补齐替代品

**本适配阶段的妥协**：
- 配方骨架（conanfile.py + conandata.yml + test_package/ + manifests）已落地
- 8 门禁只在 G0 / G1 通过，G2 受 R36 阻塞
- 给接手人：本目录的 conanfile.py 在 zlib/lua/SDL 系列迁移到 ohpcd 制品仓后**立即生效**，只需把 `self.requires(...)` 中的依赖加 `@ohpcd/stable` 后缀（每个依赖版本若 ohpcd 已发布对应版本），无需重写 conanfile.py 框架
- INSTEAD 源码目前还是 SDL2 API，跟我们已经迁好的 SDL3 链路**不兼容**。要让 INSTEAD 在 OHOS 上跑通，必须再做一次 SDL2→SDL3 的源码迁移（PR 范围外，建议单独立项）

**可选绕路**（仅 demo 用，不入正式 PR）：
- 临时在 conan-center PR 一个 OHOS-aware fork 并 upstream 接受
- 或在 ohpcd 内部 fork 起 SDL/Lua 流水（迁移组同事认领）


## 已知限制（PR 范围内不解决）

- LuaJIT FFI / JIT 编译（OHOS 无 JIT 编译器支持）
- 任意 CP12xx locale iconv 转换（仅 UTF-8）
- GTK 文件对话框（OHOS 无 GTK）
- 俄文 `ru_RU.CP1251` locale 测试（依赖 OHOS locale 缺失）
- 主题资源 / 多语言 `.po` 文件（不打包）

## 提交约束

- 不拆 PR.md 为多次 commit
- 每个源码补丁一个 commit，含 commit message
- 单独 `docs(instead): ...` commit 收尾
