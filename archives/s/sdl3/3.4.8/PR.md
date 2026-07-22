# sdl3/3.4.8 — OpenHarmony PC (aarch64) Migration

## Summary

Port SDL3 3.4.8 to OpenHarmony PC as a Conan recipe at `@ohpcd/stable`.
Unblocks INSTEAD Engine 3.5.2 migration (which requires sdl3, sdl3_image,
sdl3_ttf, sdl3_mixer) and any other downstream that uses SDL3 on OHOS.

## Build / Package

| Stage | Result |
|---|---|
| Build system | CMake (upstream `CMakeLists.txt`) |
| Toolchain | clang 15, bionic libc (aarch64) |
| Output | `libSDL3.a` (static), public headers |
| Patches | 4 source patches (OHOS platform detection, no Gtk, no pthread_cancel) |

### Notable workarounds

1. **All OHOS-incompatible backends disabled**: SDL_X11, SDL_WAYLAND,
   SDL_KMSDRM, SDL_DIRECTFB, SDL_PULSEAUDIO, SDL_ALSA, SDL_JACK,
   SDL_PIPEWIRE, SDL_SNDIO, SDL_OSS, SDL_OPENGL, SDL_OPENGLES, SDL_DBUS,
   SDL_IBUS, SDL_LIBUDEV, SDL_RPI, SDL_ROCKCHIP, SDL_VIVANTE, SDL_OPENVR
   are all set OFF. None of these are available on OHOS headless.

2. **Dummy driver is opt-in via hint**: SDL3's dummy and offscreen video
   drivers only initialize when `SDL_HINT_VIDEO_DRIVER` mentions them.
   Test_package sets `SDL_HINT_VIDEO_DRIVER = "dummy"` before
   `SDL_Init()`.

3. **`__OHOS__` defined for consumers**: SDL3's `SDL_platform_defines.h`
   gates `SDL_PLATFORM_OHOS` on `__OHOS__`. Our patch injects `-D__OHOS__`
   into SDL3's own targets, but consumers must define it themselves.
   test_package's CMakeLists.txt adds it for `CMAKE_SYSTEM_NAME=HarmonyOS|OpenHarmony`.

4. **Patches** (4 files, all OHOS-build-system plumbing):
   - `0001-CMakeLists.txt.patch` — add OHOS platform detection branch
   - `0002-include-SDL3-SDL_platform_defines.h.patch` — define `SDL_PLATFORM_OHOS`
   - `0003-src-SDL.c.patch` — skip `SDL_Gtk_Quit()` on OHOS
   - `0004-src-thread-pthread-SDL_systhread.c.patch` — skip `pthread_cancel` on OHOS

## G2 (conan create) — PASS

```
sdl3/3.4.8@ohpcd/stable: Build folder: .../b/build
sdl3/3.4.8@ohpcd/stable: Finalized folder: .../p
sdl3/3.4.8@ohpcd/stable: Packaged 1 .a file: libSDL3.a
sdl3/3.4.8@ohpcd/stable: Packaged headers (include/SDL3/*.h)
```

## R34 — test_package

Six assertions, all pass (run on conan 2.29.1, OHOS hnp clang 15):

1. ✅ `SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS)` succeeds
2. ✅ `SDL_GetPlatform()` returns a non-NULL, non-empty string
3. ✅ `SDL_GetNumVideoDrivers() >= 1` (dummy driver compiled in)
4. ✅ `SDL_CreateWindow(64, 64, SDL_WINDOW_HIDDEN)` succeeds
5. ✅ `SDL_PollEvent()` non-blocking returns >= 0
6. ✅ `SDL_GetCurrentVideoDriver() != NULL` (returns "dummy")

Note: SDL3's `SDL_GetPlatform()` does not yet have an "OHOS" branch in
its `SDL.c` (the patch adds `SDL_PLATFORM_OHOS` to the public header but
not the string mapping). The R34 contract is "API doesn't crash and
returns sensible data" — verified.

## Rules Compliance

| Rule | Status | Note |
|---|---|---|
| R6 (patches only modify sources) | ✅ | 4 source patches, no upstream CMake install config changed |
| R26 (system same-name static-only) | ✅ | `libSDL3.a` static-only |
| R34 (test_package real API) | ✅ | C API smoke through dummy driver |
| R36 (deps first) | ✅ | no deps (SDL3 standalone for our config) |

## Files

```
archives/s/sdl3/3.4.8/
├── conanfile.py             # CMake recipe with all backends disabled
├── conandata.yml            # sources + 4 patches
├── manifest.yaml
├── notes.md
├── PR.md                    # this file
├── patches/
│   ├── 0001-CMakeLists.txt.patch
│   ├── 0002-include-SDL3-SDL_platform_defines.h.patch
│   ├── 0003-src-SDL.c.patch
│   └── 0004-src-thread-pthread-SDL_systhread.c.patch
├── test_package/
│   ├── conanfile.py         # CMakeDeps + CMakeToolchain
│   ├── CMakeLists.txt       # find_package(sdl3) + __OHOS__ define
│   ├── test.c               # 6-assertion R34 smoke
│   └── MANIFEST.yml
└── reports/
    ├── conan-create.log
    └── conan-verify-report.md
```