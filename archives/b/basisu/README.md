# Basis Universal

Basis Universal is a high-performance texture compression codec supporting GPU texture format supercompression.

## Description

Basis Universal compresses textures to KTX2 format, supporting BC7, ETC2, ASTC and other GPU texture formats. Widely used in game engines and WebGL content delivery.

## Compiled Versions

- v2_1_0r (2026-08-05, Conan recipe added)

## Features

- Texture supercompression (transcoding to BC7/ETC2/ASTC)
- KTX2 format support
- High-performance codec
- WebGL and game engine compatible

## Usage

```bash
# Compress texture
basisu input.png -o output.ktx2
```
