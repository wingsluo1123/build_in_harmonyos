# SDL2_ttf

SDL2_ttf is a library that provides support for TrueType fonts in SDL2 applications.

## Dependencies

- SDL2 2.30.0 (required)
- FreeType 26.6.20 (external)
- HarfBuzz 14.2.0 (external)
- libpng 16.39.0
- zlib 1.3.1

## Available Versions

| Version | Status | Build System | Notes |
|---------|--------|--------------|-------|
| 2.24.0 | published | cmake | External FreeType + HarfBuzz; autotools fails on HMDFS |

## Installation

```bash
# Install dependencies first
curl -fsSL "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh" | sh -s -- SDL2 2.30.0

# Build SDL2_ttf (cmake required, autotools fails on HMDFS)
cd ~/builds/SDL2_ttf-2.24.0.work
cmake -B build -DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DSDL2TTF_HARFBUZZ=ON -DSDL2TTF_FREETYPE=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build -j4
cmake --install build --prefix $HOME/usr/local
```

## Notes

- Uses external FreeType and HarfBuzz (not bundled)
- CMake is required — autotools configure fails on HMDFS (config.status cannot create temp files)
- Requires config.guess patch for HarmonyOS platform recognition
