# sdl3_image 3.4.4 — OpenHarmony PC Conan 配方

## 概述
将 SDL3_image 3.4.4 适配为 OpenHarmony PC (aarch64) 的 Conan 配方。
SDL3_image 是 SDL3 的图片加载伴侣库，INSTEAD 引擎需要它来加载
PNG/JPG 等游戏素材。

- 仓库: https://github.com/libsdl-org/SDL_image
- 版本: 3.4.4 (release-3.4.4 tag)
- SHA256: `b0c11bbde540e26d1cedf31174349fe6ab67e57658efe22e16e75172859c817d`

## 依赖
- `sdl3/3.4.8@ohpcd/stable` — 同仓库迁移的 SDL3
- `zlib/1.3.1@ohpcd/stable` — 同仓库迁移的 zlib（替代 SDL3_image 自带的 external/zlib）

## 配方要点
- `generators = "CMakeDeps"`：必须，让 SDL3_image 的 CMakeLists.txt 通过
  `find_package(SDL3)` 找到 sdl3 导出的 `SDL3Config.cmake`。
- `SDLIMAGE_VENDORED=OFF`：禁用 SDL3_image 自带的 external/zlib（没有
  CMakeLists.txt），改用 conan 的 zlib/1.3.1。
- 轻量格式全开：`BMP/GIF/JPG/LBM/PCX/PNG/PNM/QOI/TGA/XCF/XPM/XV`。
- 重格式关闭：`WEBP/AVIF/JXL/TIF/SVG`（避免引入额外的 vendored 依赖、
  拉长构建时间）。
- `SDLIMAGE_BACKEND_STB=ON`：用 stb_image 做 JPEG 解码，不依赖 libjpeg-turbo。
- `shared=False`：静态库，符合 R26 静态链接规范。
- 不需要打 patch：SDL3_image 不做平台检测，沿用上游 SDL3 的 `HarmonyOS`
  平台名即可。

## test_package
- `find_package(sdl3_image REQUIRED)`（conan 的 CMakeDeps 生成小写文件）
- `target_link_libraries(test_sdl3_image sdl3_image::sdl3_image)`
- R34 满足：test_package/conanfile.py 使用 `self.tested_reference_str`。
- 二进制直接 `self.run`，并 `add_test` 注册 CTest。

## conan-verify 结果
```
✅ 配方验证通过: sdl3_image 3.4.4
   可标记 status: published
```
所有 8 门禁（G0–G7）通过，L2 smoke test / L4 checksec / L5 baseline
均通过。

## 配套改动
sdl3 配方 `package_info()` 改用 `cmake_build_modules` 属性（而不是
已被 CMakeDeps 忽略的旧 `cpp_info.build_modules["cmake"]`），才能让
`SDL3::Headers` 目标通过 `include(SDL3headersTargets.cmake)` 注入
消费者项目。这是 SDL3_image / SDL3_ttf / SDL3_mixer 共用的前置。

## 关联
- 上游：https://github.com/libsdl-org/SDL_image
- INSTEAD 引擎依赖：https://github.com/instead-hub/instead