# The new Shibata SSRC filters

## Description

`dither` can use a range of Shibata filters to improve the signal-to-noise
ratio, and [github/shibatch/ssrc](https://shibatch.github.io/ssrc) have
[coefficients for a wider range of sample rates and filter intensities](https://github.com/shibatch/SSRC/blob/master/shapercoefs.h) and their versions of
ones already in SoX are believed to be slightly better.

See [issue 493: *Import new Shibata shapes*](https://codeberg.org/sox_ng/sox_ng/issues/493).

## Summary

ATH curve A is supported at intensities 0 and 1 at 8000, 11025 and 22050 Hz,
ATH curves A and B at intensities 0 to 6 at 44100 and 48000 Hz and
ATH curve A at intensities 0, 1 and 2 at 88200, 96000 and 192000 Hz.

## Full list

| Hertz | ? | Type | Name | Points |
| -: | :-: | :- | :- | :-: |
| 8000 | 0 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 0 | 8 |
| 8000 | 1 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 1 | 7 |
| 8000 | 9 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Saturated | 16 |
| 8000 | 98 | `LIBDITHER_TYPE_SIMPLE` | Simple triangular | 1 |
| 8000 | 99 | `LIBDITHER_TYPE_SIMPLE` | No shaper | 0 |
| 11025 | 0 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 0 | 8 |
| 11025 | 1 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 1 | 6 |
| 11025 | 9 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Saturated | 16 |
| 11025 | 98 | `LIBDITHER_TYPE_SIMPLE` | Simple triangular | 1 |
| 11025 | 99 | `LIBDITHER_TYPE_SIMPLE` | No shaper | 0 |
| 22050 | 0 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 0 | 7 |
| 22050 | 1 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 1 | 12 |
| 22050 | 9 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Saturated | 16 |
| 22050 | 98 | `LIBDITHER_TYPE_SIMPLE` | Simple triangular | 1 |
| 22050 | 99 | `LIBDITHER_TYPE_SIMPLE` | No shaper | 0 |
| 44100 | 0 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 0 | 12 |
| 44100 | 1 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 1 | 12 |
| 44100 | 2 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 2 | 24 |
| 44100 | 3 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 3 | 16 |
| 44100 | 4 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 4 | 20 |
| 44100 | 5 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 5 | 16 |
| 44100 | 6 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 6 | 20 |
| 44100 | 10 | `LIBDITHER_TYPE_ATH_B` | ATH Curve B, Intensity 0 | 12 |
| 44100 | 11 | `LIBDITHER_TYPE_ATH_B` | ATH Curve B, Intensity 1 | 11 |
| 44100 | 12 | `LIBDITHER_TYPE_ATH_B` | ATH Curve B, Intensity 2 | 20 |
| 44100 | 13 | `LIBDITHER_TYPE_ATH_B` | ATH Curve B, Intensity 3 | 20 |
| 44100 | 14 | `LIBDITHER_TYPE_ATH_B` | ATH Curve B, Intensity 4 | 23 |
| 44100 | 15 | `LIBDITHER_TYPE_ATH_B` | ATH Curve B, Intensity 5 | 20 |
| 44100 | 16 | `LIBDITHER_TYPE_ATH_B` | ATH Curve B, Intensity 6 | 24 |
| 44100 | 90 | `LIBDITHER_TYPE_OLD` | ATH Curve A (Old Low) | 15 |
| 44100 | 91 | `LIBDITHER_TYPE_OLD` | ATH Curve A (Old Mid) | 20 |
| 44100 | 92 | `LIBDITHER_TYPE_OLD` | ATH Curve A (Old High) | 20 |
| 44100 | 98 | `LIBDITHER_TYPE_SIMPLE` | Simple triangular | 1 |
| 44100 | 99 | `LIBDITHER_TYPE_SIMPLE` | No shaper | 0 |
| 48000 | 0 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 0 | 16 |
| 48000 | 1 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 1 | 16 |
| 48000 | 2 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 2 | 16 |
| 48000 | 3 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 3 | 19 |
| 48000 | 4 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 4 | 28 |
| 48000 | 5 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 5 | 20 |
| 48000 | 6 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 6 | 28 |
| 48000 | 10 | `LIBDITHER_TYPE_ATH_B` | ATH Curve B, Intensity 0 | 12 |
| 48000 | 11 | `LIBDITHER_TYPE_ATH_B` | ATH Curve B, Intensity 1 | 11 |
| 48000 | 12 | `LIBDITHER_TYPE_ATH_B` | ATH Curve B, Intensity 2 | 16 |
| 48000 | 13 | `LIBDITHER_TYPE_ATH_B` | ATH Curve B, Intensity 3 | 16 |
| 48000 | 14 | `LIBDITHER_TYPE_ATH_B` | ATH Curve B, Intensity 4 | 20 |
| 48000 | 15 | `LIBDITHER_TYPE_ATH_B` | ATH Curve B, Intensity 5 | 20 |
| 48000 | 16 | `LIBDITHER_TYPE_ATH_B` | ATH Curve B, Intensity 6 | 16 |
| 48000 | 90 | `LIBDITHER_TYPE_OLD` | ATH Curve A (Old Low) | 16 |
| 48000 | 91 | `LIBDITHER_TYPE_OLD` | ATH Curve A (Old Mid) | 16 |
| 48000 | 98 | `LIBDITHER_TYPE_SIMPLE` | Simple triangular | 1 |
| 48000 | 99 | `LIBDITHER_TYPE_SIMPLE` | No shaper | 0 |
| 88200 | 0 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 0 | 24 |
| 88200 | 1 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 1 | 32 |
| 88200 | 2 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 2 | 20 |
| 88200 | 98 | `LIBDITHER_TYPE_SIMPLE` | Simple triangular | 1 |
| 88200 | 99 | `LIBDITHER_TYPE_SIMPLE` | No shaper | 0 |
| 96000 | 0 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 0 | 32 |
| 96000 | 1 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 1 | 24 |
| 96000 | 2 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 2 | 31 |
| 96000 | 98 | `LIBDITHER_TYPE_SIMPLE` | Simple triangular | 1 |
| 96000 | 99 | `LIBDITHER_TYPE_SIMPLE` | No shaper | 0 |
| 192000 | 0 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 0 | 20 |
| 192000 | 1 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 1 | 44 |
| 192000 | 2 | `LIBDITHER_TYPE_ATH_A` | ATH Curve A, Intensity 2 | 54 |
| 192000 | 98 | `LIBDITHER_TYPE_SIMPLE` | Simple triangular | 1 |
| 192000 | 99 | `LIBDITHER_TYPE_SIMPLE` | No shaper | 0 |
