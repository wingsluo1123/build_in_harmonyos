# wavplay

`wavplay` is a WAV file player (`wavplay`) and recorder (`wavrec`). The
original implementation uses the OSS (Open Sound System) `/dev/dsp` backend,
which does not exist on OpenHarmony PC; this adaptation rewrites the audio
backend to the native `OH_AudioRenderer` / `OH_AudioCapturer` API so playback
and recording are real (not stubbed).

## Versions

| Version | Status |
| --- | --- |
| 2.0 | built |

Homepage: https://sourceforge.net/projects/wavplay/
