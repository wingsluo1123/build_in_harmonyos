# sdl3_mixer 3.2.4 — OpenHarmony PC Conan 配方

## 概述
将 SDL3_mixer 3.2.4 适配为 OpenHarmony PC (aarch64) 的 Conan 配方。
SDL3_mixer 是 SDL3 的音频混音伴侣，INSTEAD 用它播放游戏音效 /
BGM。

- 仓库: https://github.com/libsdl-org/SDL_mixer
- 版本: 3.2.4 (release-3.2.4 tag)
- SHA256: `f2ea848ccdf2f394cd4973ee0f6c482e04511044695cccfd46bab6dcd7f780aa`

## 依赖
- `sdl3/3.4.8@ohpcd/stable` — 同仓库迁移的 SDL3

## 配方要点
- `generators = "CMakeDeps"`：必须，让 SDL3_mixer 的 CMakeLists.txt 通过
  `find_package(SDL3)` 找到 sdl3 导出的 `SDL3Config.cmake`。
- **只启用内建 decoder**：WAVE/AIFF/VOC/AU。这些是 SDL3_mixer 自带的
  纯 C 解码器，不需要第三方依赖。
- **关闭全部第三方 backend**：FLAC/GME/MOD/MP3/OGG(Opus)/Opus/
  WavPack/FluidSynth/Vorbis。这些都依赖外部库（libFLAC、libvorbis、
  libopus、libgme、libxmp、libmpg123、fluidsynth、wavpack），本仓库
  没有迁移它们的 conan 配方，vendor 又要走
  `external/download.sh`（git submodule clone，CI 上不可靠）。
- `SDLMIXER_VENDORED=OFF`：不 vendor 任何第三方库。
- `shared=False`：静态库，符合 R26 静态链接规范。
- 不需要打 patch：SDL3_mixer 不做平台检测，沿用上游 SDL3 的
  `HarmonyOS` 平台名即可。

## test_package
- `find_package(sdl3_mixer REQUIRED)`（conan 的 CMakeDeps 生成小写文件）
- `target_link_libraries(test_sdl3_mixer sdl3_mixer::sdl3_mixer)`
- R34 满足：test_package/conanfile.py 使用 `self.tested_reference_str`。
- test.c 用 `extern void *MIX_CreateMixer(void *device);` 触发链接，
  不强制要求 SDL3 include path 暴露。注意 SDL3_mixer 3.x 已把 API
  从 `Mix_*` 改名为 `MIX_*`，test.c 用的是新名。

## 已知限制
- 不支持 OGG(Vorbis)/Opus/MP3/FLAC 等压缩格式音频。INSTEAD 如果用
  OGG BGM，需要后续补一个 libvorbis + libogg 的 conan 配方，再把
  `SDLMIXER_OGG` 打开。当前 PR 优先让 INSTEAD 能链接通过，音频
  解码能力以后按需扩展。

## conan-verify 结果
```
✅ 配方验证通过: sdl3_mixer 3.2.4
   可标记 status: published
```
所有 8 门禁（G0–G7）通过，L2 smoke test / L4 checksec / L5 baseline
均通过。

## 关联
- 上游：https://github.com/libsdl-org/SDL_mixer
- sdl3 依赖：feat/sdl3-3.4.8