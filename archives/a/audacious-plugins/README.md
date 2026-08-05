# audacious-plugins

audacious-plugins is a collection of plugins for the Audacious audio player, providing various input/output codecs, effects, and transport support.

## Available versions
- 4.5.1 (built, 2026-08-05)

## Description
audacious-plugins provides essential functionality for audacious, including:
- Input plugins: FLAC, Vorbis, MP3 (via mpg123), Opus, WavPack, FFmpeg, Game Music Emu (console), PSF, VTX, XSF, Metronom, Tone Generator
- Output plugins: ALSA, OSS4, FileWriter (WAV/MP3/Vorbis/FLAC)
- Effect plugins: Background Music, Bitcrusher, Compressor, Crossfade, Crystalizer, Echo, Mixer, Silence Removal, Stereo, Voice Removal
- General plugins: MPRIS 2, Song Change
- Container plugins: ASX, ASX3, AudPL, M3U, PLS, XSPF
- Transport plugins: GIO, neon (HTTP/HTTPS)

## Dependencies
- audacious >= 4.5 (required)
- glib-2.0 >= 2.32
- libmpg123 >= 1.12 (for MP3)
- vorbis/vorbisenc/vorbisfile >= 1.0 (for Ogg Vorbis)
- flac >= 1.2.1 (for FLAC)
- opusfile >= 0.4 (for Opus)
- wavpack >= 4.31 (for WavPack)
- libavcodec/libavformat/libavutil (for FFmpeg)
- alsa >= 1.0.16 (for ALSA output)
- neon >= 0.27 (for HTTP/HTTPS transport)
- libxml-2.0 (for XSPF playlists)
- zlib (for Console/GME)
- openssl >= 3.0 (for neon HTTPS)

## Conan dependencies status
Available in ohpcd: glib, flac, libxml2, opus, opusfile, ffmpeg, zlib
Not in ohpcd (require separate adaptation): audacious, mpg123, libvorbis, alsa-lib, wavpack, neon, openssl, pcre2, libffi, libogg
