# SDL3_ttf

## Description
SDL3_ttf is a library that provides font rendering capabilities for SDL3 applications. It supports TrueType fonts and integrates with FreeType2 and HarfBuzz for advanced text shaping.

## Homepage
https://github.com/libsdl-org/SDL_ttf

## License
zlib license

## Dependencies

### Required
- SDL3 >= 3.2.6
- FreeType2
- HarfBuzz

### Optional
- plutosvg (for color emoji support)

## Versions

### 3.2.2
- Build Date: 2026-05-29
- Status: published
- Build System: CMake
- Build Type: Static Library

## Build Configuration
- CMAKE_SYSTEM_NAME: Linux
- CMAKE_SYSTEM_PROCESSOR: aarch64
- SDLTTF_SAMPLES: OFF
- SDLTTF_VENDORED: OFF
- BUILD_SHARED_LIBS: OFF

## Notes
- Static library build to avoid dynamic linking issues on HarmonyOS
- Depends on system freetype2 and harfbuzz libraries
- Requires SDL3, zlib, and libpng for linking

## Installation
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- sdl3-ttf 3.2.2
```