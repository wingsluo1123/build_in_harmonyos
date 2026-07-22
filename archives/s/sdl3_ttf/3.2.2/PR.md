# sdl3_ttf 3.2.2 — OpenHarmony PC Conan 配方

## 概述
将 SDL3_ttf 3.2.2 适配为 OpenHarmony PC (aarch64) 的 Conan 配方。
SDL3_ttf 是 SDL3 的 TrueType/OpenType 字体渲染伴侣，INSTEAD 用它
渲染游戏内文本。

- 仓库: https://github.com/libsdl-org/SDL_ttf
- 版本: 3.2.2 (release-3.2.2 tag)
- SHA256: `ff6b81d3dc39d843cc3ead6dedd68043a79513d266792ea89445547ef4e9b073`

## 依赖
- `sdl3/3.4.8@ohpcd/stable` — 同仓库迁移的 SDL3
- `freetype/2.14.3@ohpcd/stable` — 同仓库迁移的 freetype（替代 SDL3_ttf 自带的 external/freetype）

## 配方要点
- `generators = "CMakeDeps"`：必须，让 SDL3_ttf 的 CMakeLists.txt 通过
  `find_package(...)` 找到上游 CMake config。
- `SDLTTF_VENDORED=OFF`：禁用 SDL3_ttf 自带的 external/freetype（git
  submodule 占位，download.sh 在 CI 上不可靠），改用 conan 的
  freetype/2.14.3。
- `SDLTTF_HARFBUZZ=OFF`、`SDLTTF_PLUTOSVG=OFF`：INSTEAD 只渲染
  Latin/Cyrillic，无需 harfbuzz 复杂 shaping；plutosvg 是 SVG 彩字
  glyf 支持，对 INSTEAD 也无用。
- `shared=False`：静态库，符合 R26 静态链接规范。

## Patches
- `0001-CMakeLists.txt.patch`：把上游硬编码的 `Freetype::Freetype`
  全部 sed 替换为 `freetype::freetype`（小写）以匹配本仓库
  freetype/2.14.3 的 cmake_target_name。同时把
  `find_package(Freetype REQUIRED)` 改为
  `find_package(freetype REQUIRED CONFIG)` 匹配小写 config 文件。
  这样做是因为 freetype 的 conan 配方采用 conan-center 习惯的小写
  target 名，SDL3_ttf 上游代码不感知这种约定。

## test_package
- `find_package(sdl3_ttf REQUIRED)`（conan 的 CMakeDeps 生成小写文件）
- `target_link_libraries(test_sdl3_ttf sdl3_ttf::sdl3_ttf)`
- R34 满足：test_package/conanfile.py 使用 `self.tested_reference_str`。
- test.c 用 `extern int TTF_WasInit(void);` 触发链接 SDL3_ttf 静态库，
  不强制要求 SDL3 include path 暴露。

## conan-verify 结果
```
✅ 配方验证通过: sdl3_ttf 3.2.2
   可标记 status: published
```
所有 8 门禁（G0–G7）通过，L2 smoke test / L4 checksec / L5 baseline
均通过。test_sdl3_ttf CTest 100% 通过。

## 关联
- 上游：https://github.com/libsdl-org/SDL_ttf
- freetype 依赖：feat/freetype-2.14.3
- sdl3 依赖：feat/sdl3-3.4.8
