# SDL3_mixer

SDL3_mixer is the audio mixer extension library for SDL3.

## Description

SDL3_mixer is a library that provides audio mixing and playback capabilities for various audio formats including:
- WAV/AIFF/VOC/AU (built-in)
- FLAC (drflac backend)
- MP3 (drmp3 backend)
- Vorbis (stb_vorbis + vorbisfile)
- MIDI (timidity backend)

## Version

- 3.2.0 (official release)

## Dependencies

- sdl3 >= 3.4.0

## Build System

- CMake (pure CMake project, no autotools)

## Platform Notes

- Requires `CMAKE_SYSTEM_NAME=Linux` for HarmonyOS compatibility
- Modify `cmake/sdlplatform.cmake` to add HarmonyOS detection

## License

- zlib license (see LICENSE.txt)