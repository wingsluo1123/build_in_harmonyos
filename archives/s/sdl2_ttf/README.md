# SDL2_ttf

SDL2_ttf is a TrueType font rendering library for SDL2.

## Description

SDL2_ttf is a library that provides a simple API for loading and rendering TrueType fonts with SDL2. It wraps the FreeType and HarfBuzz libraries to provide high-quality text rendering capabilities.

## Features

- TrueType font loading and rendering
- Support for UTF-8 text
- HarfBuzz integration for complex text shaping
- High-quality glyph rendering

## Dependencies

- SDL2 (>= 2.0.10)
- FreeType2
- HarfBuzz
- libpng
- zlib

## Available Versions

| Version | Status | Build Date |
|---------|--------|------------|
| 2.24.0 | built | 2026-05-27 |

## Usage

```c
#include <SDL2/SDL_ttf.h>

// Initialize SDL_ttf
TTF_Init();

// Load a font
TTF_Font* font = TTF_OpenFont("font.ttf", 24);

// Render text
SDL_Surface* surface = TTF_RenderText_Blended(font, "Hello World", color);

// Clean up
TTF_CloseFont(font);
TTF_Quit();
```

## License

MIT License

## Links

- Official Website: https://wiki.libsdl.org/SDL_ttf
- Source Code: https://github.com/libsdl-org/SDL_ttf